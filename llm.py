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
    client: Any, settings: Settings, messages: list[dict[str, str]]
) -> Any:
    """发起一次对话请求，返回流式响应对象。

    这里刻意把 model / temperature / stream 显式写出来，
    便于单元测试断言「确实按配置传参」。
    """
    return client.chat.completions.create(
        model=settings.model,
        messages=messages,
        temperature=settings.temperature,
        stream=settings.stream,
        **({"max_tokens": settings.max_tokens} if settings.max_tokens else {}),
    )


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
