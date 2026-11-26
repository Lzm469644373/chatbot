"""把对话历史整理成发给模型的 messages。

命令行入口（chat.py）和 HTTP 服务（app/）共用这一份逻辑，
避免两套裁剪规则不一致。
"""

from __future__ import annotations

from config import Settings


def build_initial_messages(settings: Settings) -> list[dict[str, str]]:
    """对话初始只有一条 system 消息，它决定了助手的人设。"""
    return [{"role": "system", "content": settings.system_prompt}]


def trim_history(
    messages: list[dict[str, str]], max_messages: int
) -> list[dict[str, str]]:
    """裁剪历史，但**永远保留 system 消息**。

    只保留最近的 ``max_messages - 1`` 条对话，避免上下文无限增长导致超长报错。
    """
    if len(messages) <= max_messages:
        return messages

    system_messages = [m for m in messages if m["role"] == "system"]
    dialog = [m for m in messages if m["role"] != "system"]
    keep = max(1, max_messages - len(system_messages))
    return system_messages + dialog[-keep:]


def build_request_messages(
    settings: Settings,
    history: list[dict[str, str]],
    user_message: str,
) -> list[dict[str, str]]:
    """拼出本轮请求：system + 历史 + 本轮用户消息，再按配置裁剪。"""
    messages = build_initial_messages(settings)
    messages.extend(dict(m) for m in history)
    messages.append({"role": "user", "content": user_message})
    return trim_history(messages, settings.max_history_messages)
