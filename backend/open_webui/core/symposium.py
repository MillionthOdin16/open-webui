import asyncio
import json
import logging
import time
import uuid
import re
from typing import Dict, Optional, List

from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse, JSONResponse

from open_webui.models.chats import Chats
from open_webui.models.users import Users
from open_webui.utils.chat import generate_chat_completion
from open_webui.socket.main import get_event_emitter, sio
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

class MockRequest:
    def __init__(self, app):
        self.app = app
        self.state = type('MockState', (), {})()

class SymposiumManager:
    def __init__(self):
        self.active_symposiums: Dict[str, asyncio.Task] = {}
        self.overrides: Dict[str, str] = {}
        self.app = None

    def init_app(self, app):
        self.app = app

    async def set_next_speaker(self, chat_id: str, model_id: str):
        self.overrides[chat_id] = model_id

    async def start_symposium(self, chat_id: str):
        if chat_id in self.active_symposiums:
            return

        log.info(f"Starting symposium for chat {chat_id}")
        task = asyncio.create_task(self.symposium_loop(chat_id))
        self.active_symposiums[chat_id] = task

    async def stop_symposium(self, chat_id: str):
        if chat_id in self.active_symposiums:
            log.info(f"Stopping symposium for chat {chat_id}")
            self.active_symposiums[chat_id].cancel()
            try:
                await self.active_symposiums[chat_id]
            except asyncio.CancelledError:
                pass
            del self.active_symposiums[chat_id]

    async def symposium_loop(self, chat_id: str):
        try:
            while True:
                try:
                    chat = await run_in_threadpool(Chats.get_chat_by_id, chat_id)
                    if not chat or chat.archived:
                        await self.stop_symposium(chat_id)
                        break

                    config = chat.config or {}
                    if config.get("paused", False):
                        await asyncio.sleep(2)
                        continue

                    interval = int(config.get('autonomous_interval', 30))
                    models = config.get('models', [])

                    if not models:
                        log.warning(f"No models in symposium {chat_id}")
                        await asyncio.sleep(interval)
                        continue

                    history = chat.chat.get('history', {}).get('messages', {})
                    sorted_messages = sorted(history.values(), key=lambda x: x.get('timestamp', 0))

                    next_model_id = models[0]
                    override_model = self.overrides.pop(chat_id, None)

                    if override_model and override_model in models:
                        next_model_id = override_model
                    elif sorted_messages:
                        last_msg = sorted_messages[-1]

                        # Check for tags in content to override speaker
                        content = last_msg.get('content', '')
                        tags = re.findall(r'@(?:"([^"]+)"|([a-zA-Z0-9_.:-]+))', content)
                        valid_tags = [t[0] or t[1] for t in tags]

                        for tag in valid_tags:
                            for m_id in models:
                                if tag.lower() in m_id.lower():
                                    override_model = m_id
                                    break
                            if override_model:
                                break

                        if override_model:
                            next_model_id = override_model
                        else:
                            last_model = last_msg.get('model')
                            if last_model in models:
                                try:
                                    idx = models.index(last_model)
                                    next_model_id = models[(idx + 1) % len(models)]
                                except ValueError:
                                    pass
                            else:
                                next_model_id = models[0]

                    context_limit = 10
                    recent_msgs = sorted_messages[-context_limit:]

                    messages_payload = []

                    system_prompt = config.get('prompt', 'You are in a symposium.')
                    system_prompt += f"\n\nParticipants: {', '.join(models)}"
                    messages_payload.append({"role": "system", "content": system_prompt})

                    for msg in recent_msgs:
                        content = msg.get('content', '')
                        author_name = msg.get('modelName') or msg.get('model') or 'User'
                        if msg.get('role') == 'user':
                            author_name = "User"

                        messages_payload.append({
                            "role": "user",
                            "content": f"[{author_name}]: {content}"
                        })

                    user = await run_in_threadpool(Users.get_user_by_id, chat.user_id)
                    request = MockRequest(self.app)
                    request.state.metadata = {
                        "chat_id": chat_id,
                        "session_id": "symposium-autonomy",
                        "user_id": chat.user_id
                    }

                    form_data = {
                        "model": next_model_id,
                        "messages": messages_payload,
                        "stream": False,
                    }

                    log.info(f"Symposium {chat_id}: Generating response from {next_model_id}")

                    await sio.emit(
                        "symposium:status",
                        {
                            "chat_id": chat_id,
                            "model": next_model_id,
                            "status": "Generating...",
                        },
                    )

                    response = await generate_chat_completion(request, form_data, user)

                    content = ""
                    if isinstance(response, StreamingResponse):
                        async for chunk in response.body_iterator:
                            if isinstance(chunk, bytes):
                                chunk = chunk.decode('utf-8', errors='ignore')

                            for line in chunk.split('\n'):
                                if line.startswith('data: '):
                                    data_str = line[6:]
                                    if data_str == '[DONE]':
                                        continue
                                    try:
                                        data = json.loads(data_str)
                                        if 'choices' in data:
                                            delta = data['choices'][0].get('delta', {}).get('content', '')
                                            content += delta
                                        elif 'content' in data:
                                            content += data['content']
                                    except:
                                        pass
                    elif isinstance(response, JSONResponse):
                        body = json.loads(response.body)
                        if 'choices' in body:
                            content = body['choices'][0]['message']['content']
                    elif isinstance(response, dict):
                        if 'choices' in response:
                            content = response['choices'][0]['message']['content']
                        elif 'content' in response:
                            content = response['content']

                    if content:
                        message_id = str(uuid.uuid4())
                        message = {
                            "id": message_id,
                            "parentId": recent_msgs[-1]['id'] if recent_msgs else None,
                            "childrenIds": [],
                            "role": "assistant",
                            "content": content,
                            "model": next_model_id,
                            "modelName": next_model_id,
                            "timestamp": int(time.time())
                        }

                        await run_in_threadpool(
                            Chats.upsert_message_to_chat_by_id_and_message_id,
                            chat_id, message_id, message
                        )

                        if message['parentId']:
                            parent = await run_in_threadpool(
                                Chats.get_message_by_id_and_message_id,
                                chat_id, message['parentId']
                            )
                            if parent:
                                parent['childrenIds'] = parent.get('childrenIds', []) + [message_id]
                                await run_in_threadpool(
                                    Chats.upsert_message_to_chat_by_id_and_message_id,
                                    chat_id, message['parentId'], parent
                                )

                        event_emitter = get_event_emitter({
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "user_id": chat.user_id
                        })

                        if event_emitter:
                            await event_emitter({
                                "type": "chat:tags",
                                "data": {}
                            })

                except Exception as e:
                    log.error(f"Error in symposium loop for {chat_id}: {e}")

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            log.info(f"Symposium loop cancelled for {chat_id}")

    async def splice_message(self, chat_id: str, content: str, user_id: str):
        chat = await run_in_threadpool(Chats.get_chat_by_id, chat_id)
        if not chat:
            return False

        history = chat.chat.get('history', {}).get('messages', {})
        sorted_messages = sorted(history.values(), key=lambda x: x.get('timestamp', 0))

        parent_id = sorted_messages[-1]['id'] if sorted_messages else None

        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "parentId": parent_id,
            "childrenIds": [],
            "role": "system",
            "content": f"_{content}_",
            "model": "system_echo",
            "modelName": "Echo",
            "timestamp": int(time.time()),
            "type": "echo"
        }

        await run_in_threadpool(
            Chats.upsert_message_to_chat_by_id_and_message_id,
            chat_id, message_id, message
        )

        if parent_id:
            parent = await run_in_threadpool(
                Chats.get_message_by_id_and_message_id,
                chat_id, parent_id
            )
            if parent:
                parent['childrenIds'] = parent.get('childrenIds', []) + [message_id]
                await run_in_threadpool(
                    Chats.upsert_message_to_chat_by_id_and_message_id,
                    chat_id, parent_id, parent
                )

        # Emit symposium message for real-time update
        await sio.emit("symposium:message", {"chat_id": chat_id, "message": message})
        return True

symposium_manager = SymposiumManager()
