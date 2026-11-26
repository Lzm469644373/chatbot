"""业务逻辑：把「取历史 → 调模型 → 写历史」串起来，路由层只做参数与响应。

放在 service 层而不是写进路由，是为了让 CLI、HTTP、以后的定时任务复用同一套流程。
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.store import SessionStore
from config import Settings
from conversation import build_request_messages
from llm import (
    complete_text,
    create_completion,
    extract_reply,
    iter_delta_text,
)


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

    # 一轮对话原子写入，避免并发请求读到「只有提问没有回复」的半截历史
    store.append_turn(session_id, message, reply)
    return reply


def open_stream(
    client: Any,
    settings: Settings,
    store: SessionStore,
    session_id: str,
    message: str,
) -> Any:
    """发起流式请求并先把用户消息写入历史。

    注意：``create_completion`` 必须在返回 ``StreamingResponse`` 之前调用，
    这样连接失败 / Key 无效还能变成正常的 502/503；放进生成器里就来不及了。
    """
    history = store.get(session_id) or []
    messages = build_request_messages(settings, history, message)

    stream = create_completion(client, settings, messages, stream=True)
    store.append(session_id, "user", message)
    return stream


def iter_reply(
    stream: Any,
    store: SessionStore,
    session_id: str,
) -> Iterator[str]:
    """边转发分片边收集，结束后把完整回复写入历史。

    用 ``finally`` 保证正常结束、出错、客户端断开三种情况都会落库
    （中途断开时保存已经生成的部分）。
    """
    collected: list[str] = []
    try:
        for piece in iter_delta_text(stream):
            collected.append(piece)
            yield piece
    finally:
        reply = "".join(collected)
        if reply:
            store.append(session_id, "assistant", reply)


def explain_word(client: Any, settings: Settings, word: str) -> str:
    """学习功能：让模型讲解一个英语单词（释义 + 例句）。"""
    messages = [
        {"role": "system", "content": settings.study_system_prompt},
        {"role": "user", "content": f"单词：{word}"},
    ]
    return complete_text(client, settings, messages)
