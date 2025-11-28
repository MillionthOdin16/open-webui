import asyncio
import json
import logging
import time
import uuid
import re
from typing import Dict, Optional, List, Set
from enum import Enum

from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse, JSONResponse

from open_webui.models.chats import Chats
from open_webui.models.users import Users
from open_webui.utils.chat import generate_chat_completion
from open_webui.socket.main import get_event_emitter, sio
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class BotState(str, Enum):
    ACTIVE = "active"       # Bot participates in conversation
    LISTENING = "listening" # Bot observes but doesn't speak unless tagged
    MUTED = "muted"         # Bot is completely silent
    SPEAKING = "speaking"   # Bot is currently generating a response


class MockRequest:
    def __init__(self, app):
        self.app = app
        self.state = type('MockState', (), {})()


class SymposiumManager:
    def __init__(self):
        self.active_symposiums: Dict[str, asyncio.Task] = {}
        self.events: Dict[str, asyncio.Event] = {}
        self.overrides: Dict[str, str] = {}
        self.whispers: Dict[str, Dict[str, str]] = {}
        # Bot states per symposium: {chat_id: {model_id: BotState}}
        self.bot_states: Dict[str, Dict[str, BotState]] = {}
        # Speaking history: {chat_id: [(timestamp, model_id, word_count)]}
        self.speaking_history: Dict[str, List[tuple]] = {}
        # Current speaker for each symposium
        self.current_speakers: Dict[str, Optional[str]] = {}
        self.app = None

    def init_app(self, app):
        self.app = app

    def get_bot_state(self, chat_id: str, model_id: str) -> BotState:
        """Get the current state of a bot in a symposium."""
        if chat_id not in self.bot_states:
            return BotState.ACTIVE
        return self.bot_states.get(chat_id, {}).get(model_id, BotState.ACTIVE)

    async def set_bot_state(self, chat_id: str, model_id: str, state: BotState):
        """Set the state of a bot in a symposium."""
        if chat_id not in self.bot_states:
            self.bot_states[chat_id] = {}
        self.bot_states[chat_id][model_id] = state
        
        # Emit state change to clients
        await sio.emit(
            "symposium:bot_state",
            {
                "chat_id": chat_id,
                "model_id": model_id,
                "state": state.value,
            },
        )

    def get_all_bot_states(self, chat_id: str) -> Dict[str, str]:
        """Get all bot states for a symposium."""
        if chat_id not in self.bot_states:
            return {}
        return {k: v.value for k, v in self.bot_states.get(chat_id, {}).items()}

    def get_speaking_stats(self, chat_id: str) -> Dict[str, dict]:
        """Get speaking statistics for each bot in a symposium."""
        history = self.speaking_history.get(chat_id, [])
        stats: Dict[str, dict] = {}
        
        for timestamp, model_id, word_count in history:
            if model_id not in stats:
                stats[model_id] = {"message_count": 0, "word_count": 0, "last_spoke": 0}
            stats[model_id]["message_count"] += 1
            stats[model_id]["word_count"] += word_count
            stats[model_id]["last_spoke"] = max(stats[model_id]["last_spoke"], timestamp)
        
        return stats

    async def set_next_speaker(self, chat_id: str, model_id: str):
        self.overrides[chat_id] = model_id
        if chat_id in self.events:
            self.events[chat_id].set()

    async def add_whisper(self, chat_id: str, model_id: str, content: str):
        if chat_id not in self.whispers:
            self.whispers[chat_id] = {}
        self.whispers[chat_id][model_id] = content

    async def notify_update(self, chat_id: str):
        if chat_id in self.events:
            self.events[chat_id].set()

    def is_symposium_active(self, chat_id: str) -> bool:
        """Check if a symposium is currently active."""
        return chat_id in self.active_symposiums

    def get_current_speaker(self, chat_id: str) -> Optional[str]:
        """Get the current speaker in a symposium."""
        return self.current_speakers.get(chat_id)

    async def start_symposium(self, chat_id: str):
        if chat_id in self.active_symposiums:
            return

        log.info(f"Starting symposium for chat {chat_id}")
        self.events[chat_id] = asyncio.Event()
        self.bot_states[chat_id] = {}
        self.speaking_history[chat_id] = []
        self.current_speakers[chat_id] = None
        task = asyncio.create_task(self.symposium_loop(chat_id))
        self.active_symposiums[chat_id] = task
        
        # Notify clients that symposium is active
        await sio.emit(
            "symposium:started",
            {"chat_id": chat_id},
        )

    async def stop_symposium(self, chat_id: str):
        if chat_id in self.active_symposiums:
            log.info(f"Stopping symposium for chat {chat_id}")
            task = self.active_symposiums[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                log.debug(f"Symposium task {chat_id} cancelled successfully")
            finally:
                del self.active_symposiums[chat_id]

        # Clean up all state
        if chat_id in self.events:
            del self.events[chat_id]
        
        self.overrides.pop(chat_id, None)
        self.whispers.pop(chat_id, None)
        self.bot_states.pop(chat_id, None)
        self.speaking_history.pop(chat_id, None)
        self.current_speakers.pop(chat_id, None)
        
        # Notify clients that symposium stopped
        await sio.emit(
            "symposium:stopped",
            {"chat_id": chat_id},
        )

    async def symposium_loop(self, chat_id: str):
        event = self.events[chat_id]
        try:
            while True:
                try:
                    chat = await run_in_threadpool(Chats.get_chat_by_id, chat_id)
                    if not chat or chat.archived:
                        await self.stop_symposium(chat_id)
                        break

                    config = chat.config or {}
                    if config.get("paused", False):
                        # Wait for event if paused, no timeout needed or long timeout
                        try:
                            await asyncio.wait_for(event.wait(), timeout=3600) # Check every hour or wait for event
                            event.clear()
                        except asyncio.TimeoutError:
                            pass
                        continue

                    MIN_INTERVAL = 10  # Minimum 10 seconds to prevent API spam
                    interval = max(MIN_INTERVAL, int(config.get('autonomous_interval', 30)))
                    models = config.get('models', [])

                    if not models:
                        log.warning(f"No models in symposium {chat_id}")
                        await asyncio.sleep(interval)
                        continue

                    history = chat.chat.get('history', {}).get('messages', {})
                    # Optimize sorting for large histories
                    if len(history) > 50:
                        recent_threshold = int(time.time()) - 3600  # Last hour
                        recent_history = {k: v for k, v in history.items() 
                                          if v.get('timestamp', 0) > recent_threshold}
                        sorted_messages = sorted(recent_history.values(), key=lambda x: x.get('timestamp', 0))
                    else:
                        sorted_messages = sorted(history.values(), key=lambda x: x.get('timestamp', 0))

                    next_model_id = models[0]
                    override_model = self.overrides.pop(chat_id, None)
                    was_tagged = False

                    if override_model and override_model in models:
                        next_model_id = override_model
                        was_tagged = True
                    elif sorted_messages:
                        last_msg = sorted_messages[-1]

                        content = last_msg.get('content', '')
                        tags = re.findall(r'@(?:"([^"]+)"|([a-zA-Z0-9_.:-]+))', content)
                        valid_tags = [t[0] or t[1] for t in tags]

                        tag_override = None
                        for tag in valid_tags:
                            for m_id in models:
                                if tag.lower() in m_id.lower():
                                    tag_override = m_id
                                    was_tagged = True
                                    break
                            if tag_override:
                                break

                        if tag_override:
                            next_model_id = tag_override
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
                    
                    # Check bot state - skip if muted, or if listening and not tagged
                    bot_state = self.get_bot_state(chat_id, next_model_id)
                    if bot_state == BotState.MUTED:
                        # Find next active bot
                        active_found = False
                        for m_id in models:
                            if self.get_bot_state(chat_id, m_id) == BotState.ACTIVE:
                                next_model_id = m_id
                                active_found = True
                                break
                        if not active_found:
                            # All bots are muted or listening, wait
                            try:
                                await asyncio.wait_for(event.wait(), timeout=interval)
                                event.clear()
                            except asyncio.TimeoutError:
                                pass
                            continue
                    elif bot_state == BotState.LISTENING and not was_tagged:
                        # Listening bot - only respond if tagged, otherwise skip to next active bot
                        found_next = False
                        start_idx = models.index(next_model_id) if next_model_id in models else 0
                        for i in range(len(models)):
                            check_idx = (start_idx + i + 1) % len(models)
                            m_id = models[check_idx]
                            m_state = self.get_bot_state(chat_id, m_id)
                            if m_state == BotState.ACTIVE:
                                next_model_id = m_id
                                found_next = True
                                break
                        if not found_next:
                            # No active bots, wait
                            try:
                                await asyncio.wait_for(event.wait(), timeout=interval)
                                event.clear()
                            except asyncio.TimeoutError:
                                pass
                            continue

                    context_limit = int(config.get('context_limit', 20))
                    recent_msgs = sorted_messages[-context_limit:]

                    messages_payload = []

                    system_prompt = config.get('prompt', 'You are in a symposium.')
                    system_prompt += f"\n\nParticipants: {', '.join(models)}"

                    whisper = self.whispers.get(chat_id, {}).pop(next_model_id, None)
                    if whisper:
                        system_prompt += (
                            f"\n\nPrivate Instruction for {next_model_id}: {whisper}"
                        )

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
                    
                    # Set current speaker and update bot state
                    self.current_speakers[chat_id] = next_model_id
                    await self.set_bot_state(chat_id, next_model_id, BotState.SPEAKING)

                    await sio.emit(
                        "symposium:status",
                        {
                            "chat_id": chat_id,
                            "model": next_model_id,
                            "status": "Generating...",
                        },
                    )

                    try:
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
                                        except json.JSONDecodeError:
                                            log.debug(f"Failed to parse JSON chunk: {data_str[:100]}")
                                        except Exception as e:
                                            log.error(f"Error parsing response chunk: {e}")
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

                            # Track speaking history
                            word_count = len(content.split())
                            if chat_id not in self.speaking_history:
                                self.speaking_history[chat_id] = []
                            self.speaking_history[chat_id].append((int(time.time()), next_model_id, word_count))
                            
                            # Emit symposium message for real-time update
                            await sio.emit("symposium:message", {"chat_id": chat_id, "message": message})
                        
                        # Reset bot state from speaking to previous state (active by default)
                        prev_state = BotState.ACTIVE
                        await self.set_bot_state(chat_id, next_model_id, prev_state)
                        self.current_speakers[chat_id] = None

                        await sio.emit(
                            "symposium:status",
                            {
                                "chat_id": chat_id,
                                "model": next_model_id,
                                "status": None,
                            },
                        )
                    except Exception as e:
                        log.error(f"Symposium {chat_id}: Model {next_model_id} failed: {e}")
                        # Reset bot state on error
                        await self.set_bot_state(chat_id, next_model_id, BotState.ACTIVE)
                        self.current_speakers[chat_id] = None
                        
                        await sio.emit("symposium:status", {
                            "chat_id": chat_id,
                            "model": next_model_id,
                            "status": f"Error: {str(e)[:100]}",
                            "error": True
                        })
                        # Continue to next iteration instead of crashing
                        await asyncio.sleep(5)
                        continue

                except Exception as e:
                    log.error(f"Error in symposium loop for {chat_id}: {e}")

                # Wait for next interval OR event trigger
                try:
                    await asyncio.wait_for(event.wait(), timeout=interval)
                    event.clear()
                except asyncio.TimeoutError:
                    pass

        except asyncio.CancelledError:
            log.info(f"Symposium loop cancelled for {chat_id}")

    async def splice_message(self, chat_id: str, content: str, user_id: str):
        try:
            chat = await run_in_threadpool(Chats.get_chat_by_id, chat_id)
            if not chat:
                log.warning(f"splice_message: Chat {chat_id} not found")
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
        except Exception as e:
            log.error(f"Error splicing message to {chat_id}: {e}")
            return False

symposium_manager = SymposiumManager()
