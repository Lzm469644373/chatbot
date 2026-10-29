"""大模型调用的薄封装（PR1：一次性返回完整回复）。"""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from config import Settings, require_api_key


def build_client(settings: Settings) -> OpenAI:
    """按配置构造 OpenAI 兼容客户端。"""
    return OpenAI(
        api_key=require_api_key(settings),
        base_url=settings.base_url,
        timeout=settings.request_timeout,
    )


def create_completion(
    client: Any, settings: Settings, messages: list[dict[str, str]]
) -> Any:
    """发起一次对话请求（非流式）。"""
    return client.chat.completions.create(
        model=settings.model,
        messages=messages,
        temperature=settings.temperature,
        **({"max_tokens": settings.max_tokens} if settings.max_tokens else {}),
    )


def extract_reply(response: Any) -> str:
    """从完整响应里取出回复正文。"""
    if not response.choices:
        return ""
    return response.choices[0].message.content or ""
