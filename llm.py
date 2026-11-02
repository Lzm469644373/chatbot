"""大模型调用的薄封装。

把「构造客户端」和「发起请求」拆成两个函数，好处是单元测试可以完全绕开网络：
把假的 client 传进 ``create_completion``，直接断言传参。
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
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
    client: Any,
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    stream: bool | None = None,
) -> Any:
    """发起一次对话请求。

    ``stream`` 显式传入时以它为准（HTTP 的 ``/chat`` 需要 ``stream=False``，
    ``/chat/stream`` 需要 ``stream=True``）；不传时沿用 ``CHATBOT_STREAM``。
    model / temperature / stream 都显式写出来，便于单元测试断言「确实按配置传参」。
    """
    use_stream = settings.stream if stream is None else stream
    return client.chat.completions.create(
        model=settings.model,
        messages=messages,
        temperature=settings.temperature,
        stream=use_stream,
        **({"max_tokens": settings.max_tokens} if settings.max_tokens else {}),
    )


def extract_reply(response: Any) -> str:
    """从非流式响应中取出第一条回复文本（没有内容时返回空串）。"""
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None) if message is not None else None
    return (content or "").strip()


def iter_delta_text(stream: Iterable[Any]) -> Iterator[str]:
    """从流式响应中逐段取出文本增量。

    索引 0 上取第一个候选；遇到空 choices（例如最后的 usage 包）就跳过。
    """
    for chunk in stream:
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        text = getattr(delta, "content", None) if delta is not None else None
        if text:
            yield text
