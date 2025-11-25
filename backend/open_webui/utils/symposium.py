import asyncio
import logging
import json
import time
import uuid
import random

from fastapi import Request
from open_webui.models.chats import Chats
from open_webui.models.users import Users
from open_webui.utils.chat import generate_chat_completion
from open_webui.socket.main import get_event_emitter
from open_webui.env import SRC_LOG_LEVELS
# We import app lazily to avoid circular imports if possible, or assume it's set in state

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

SYMPOSIUM_TASKS = {}

async def start_symposium_loop(chat_id: str):
    if chat_id in SYMPOSIUM_TASKS:
        return

    log.debug(f"Starting symposium loop for {chat_id}")
    task = asyncio.create_task(symposium_autonomy(chat_id))
    SYMPOSIUM_TASKS[chat_id] = task

async def stop_symposium_loop(chat_id: str):
    if chat_id in SYMPOSIUM_TASKS:
        log.debug(f"Stopping symposium loop for {chat_id}")
        task = SYMPOSIUM_TASKS[chat_id]
        task.cancel()
        del SYMPOSIUM_TASKS[chat_id]

async def symposium_autonomy(chat_id: str):
    from open_webui.main import app

    try:
        while True:
            # Re-fetch chat to get latest config/state
            chat = Chats.get_chat_by_id(chat_id)
            if not chat or chat.mode != "symposium":
                break

            config = chat.config or {}
            if not config.get("active", True):
                await asyncio.sleep(5)
                continue

            interval = float(config.get("autonomous_interval", 10))
            models = config.get("models", [])

            if not models:
                await asyncio.sleep(5)
                continue

            # Wait for interval
            await asyncio.sleep(interval)

            # Re-check active status after sleep
            chat = Chats.get_chat_by_id(chat_id)
            if not chat: break

            # Get User
            user = Users.get_user_by_id(chat.user_id)
            if not user: break

            # History
            history = chat.chat.get("history", {})
            messages = history.get("messages", {})
            current_id = history.get("currentId")

            # Check if last message was done
            if current_id:
                last_msg = messages.get(current_id)
                if last_msg and not last_msg.get("done", True):
                    # Still generating (maybe manually triggered), wait.
                    continue

            # Determine next model
            last_model_id = None
            if current_id:
                last_msg = messages.get(current_id)
                if last_msg:
                    last_model_id = last_msg.get("model")

            next_model_id = models[0]
            if last_model_id in models:
                idx = models.index(last_model_id)
                next_model_id = models[(idx + 1) % len(models)]

            # Prepare Mock Request
            scope = {
                "type": "http",
                "headers": [],
                "app": app,
                "state": {}
            }
            mock_request = Request(scope)
            mock_request.state.user = user

            # Prepare messages list
            msgs_list = []
            curr = current_id
            while curr:
                msg = messages.get(curr)
                if not msg: break
                msgs_list.insert(0, msg)
                curr = msg.get("parentId")

            api_messages = []
            for m in msgs_list:
                api_messages.append({
                    "role": m.get("role"),
                    "content": m.get("content"),
                })

            # Prepare payload
            payload = {
                "model": next_model_id,
                "messages": api_messages,
                "chat_id": chat_id,
                "stream": True,
            }

            # Create a placeholder message for the response
            parent_id = current_id
            response_id = str(uuid.uuid4())

            response_message = {
                "id": response_id,
                "parentId": parent_id,
                "childrenIds": [],
                "role": "assistant",
                "content": "",
                "model": next_model_id,
                "modelName": next_model_id, # Simplified, should get name from models list if available
                "timestamp": int(time.time()),
                "done": False
            }

            # Save to DB (Initial)
            Chats.upsert_message_to_chat_by_id_and_message_id(
                chat_id, response_id, response_message
            )

            # Link to parent
            if parent_id:
                parent_msg = messages.get(parent_id)
                children = parent_msg.get("childrenIds", [])
                children.append(response_id)
                Chats.upsert_message_to_chat_by_id_and_message_id(
                    chat_id, parent_id, {"childrenIds": children}
                )

            event_emitter = get_event_emitter({
                "chat_id": chat_id,
                "message_id": response_id,
                "user_id": user.id
            })

            # Emit creation event
            await event_emitter({
                "type": "replace",
                "data": response_message
            })

            try:
                # Call Generate
                res = await generate_chat_completion(mock_request, payload, user)

                if hasattr(res, 'body_iterator'):
                    async for chunk in res.body_iterator:
                        # chunk is bytes
                        if isinstance(chunk, bytes):
                            text_chunk = chunk.decode("utf-8")
                        else:
                            text_chunk = str(chunk)

                        lines = text_chunk.split("\n\n")
                        for line in lines:
                            line = line.strip()
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    data_json = json.loads(data_str)
                                    content = ""
                                    if "choices" in data_json and len(data_json["choices"]) > 0:
                                         delta = data_json["choices"][0].get("delta", {})
                                         content = delta.get("content", "")

                                    if content:
                                        await event_emitter({
                                            "type": "message",
                                            "data": {"content": content}
                                        })

                                except Exception:
                                    pass
                elif isinstance(res, dict):
                     # Non-streaming
                     content = res.get("choices", [])[0].get("message", {}).get("content", "")
                     await event_emitter({
                        "type": "replace",
                        "data": {"content": content}
                    })

                # Mark done
                Chats.upsert_message_to_chat_by_id_and_message_id(
                    chat_id, response_id, {"done": True}
                )
                await event_emitter({
                    "type": "status",
                    "data": {"done": True}
                })

            except Exception as e:
                log.error(f"Generation error: {e}")
                Chats.upsert_message_to_chat_by_id_and_message_id(
                    chat_id, response_id, {"error": str(e), "done": True}
                )
                await event_emitter({
                    "type": "status",
                    "data": {"done": True, "error": str(e)}
                })

    except asyncio.CancelledError:
        log.debug(f"Symposium loop cancelled for {chat_id}")
