"""业务逻辑：把「取历史 → 调模型 → 写历史」串起来，路由层只做参数与响应。

放在 service 层而不是写进路由，是为了让 CLI、HTTP、以后的定时任务复用同一套流程。
"""

from __future__ import annotations

from typing import Any

from app.store import SessionStore
from config import Settings
from conversation import build_request_messages
from llm import create_completion, extract_reply


def chat_once(
    client: Any,
    settings: Settings,
    store: SessionStore,
    session_id: str,
    message: str,
) -> str:
    """发起一轮普通（非流式）对话，并把这一轮写入历史。

    先调模型、成功后再落库：调用失败时不会在历史里留下半截对话。
    """
    history = store.get(session_id) or []
    messages = build_request_messages(settings, history, message)

    response = create_completion(client, settings, messages, stream=False)
    reply = extract_reply(response)

    store.append(session_id, "user", message)
    store.append(session_id, "assistant", reply)
    return reply
