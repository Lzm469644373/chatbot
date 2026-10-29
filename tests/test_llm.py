"""大模型调用的单元测试：mock 掉 client，不联网、不需要真实 Key。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from config import Settings
from llm import create_completion, iter_delta_text


class FakeCompletions:
    """记录 create() 收到的参数，并返回预设的流式响应。

    注意：messages 必须**深拷贝**后再保存，否则主循环后续 append
    会改到同一个列表对象，导致断言看到的是"最终状态"而不是"调用时状态"。
    """

    def __init__(self, chunks):
        self._chunks = chunks
        self.calls: list[dict] = []

    def create(self, **kwargs):
        snapshot = dict(kwargs)
        snapshot["messages"] = [dict(m) for m in kwargs["messages"]]
        self.calls.append(snapshot)
        return iter(self._chunks)


class FakeClient:
    def __init__(self, chunks):
        self.chat = SimpleNamespace(completions=FakeCompletions(chunks))


def make_chunk(text: str | None):
    """构造一个与 OpenAI 流式分片结构一致的对象。"""
    delta = SimpleNamespace(content=text) if text is not None else SimpleNamespace(content=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test")
    monkeypatch.setenv("CHATBOT_MODEL", "deepseek-chat")
    monkeypatch.setenv("CHATBOT_TEMPERATURE", "0.3")
    return Settings()


def test_create_completion_passes_configured_parameters(settings):
    """必须按配置传 model / temperature / messages，并且开启 stream=True。"""
    client = FakeClient([make_chunk("你好")])
    messages = [
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "第一轮问题"},
    ]

    create_completion(client, settings, messages)

    assert len(client.chat.completions.calls) == 1
    kwargs = client.chat.completions.calls[0]

    assert kwargs["model"] == "deepseek-chat"
    assert kwargs["temperature"] == 0.3
    assert kwargs["stream"] is True                 # 流式输出开关必须打开
    # 调用时传给模型的消息应原样等于传入的上下文
    assert kwargs["messages"] == messages
    # 消息结构：system 在首位，user 在最后
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][-1] == {"role": "user", "content": "第一轮问题"}


def test_stream_is_off_when_configured(monkeypatch, settings):
    """CHATBOT_STREAM=false 时应传 stream=False。"""
    monkeypatch.setenv("CHATBOT_STREAM", "false")
    settings = Settings()
    client = FakeClient([])

    create_completion(client, settings, [{"role": "user", "content": "hi"}])

    assert client.chat.completions.calls[0]["stream"] is False


def test_iter_delta_text_skips_empty_choices(settings):
    """流式分片里空 content / 空 choices 都要跳过，拼接结果应完整。"""
    chunks = [
        make_chunk("你"),
        make_chunk(None),                              # 只有 role 的首包
        SimpleNamespace(choices=[]),                   # 统计信息的尾包
        make_chunk("好"),
        make_chunk("！"),
    ]

    assert "".join(iter_delta_text(iter(chunks))) == "你好！"


def test_conversation_context_is_kept(settings):
    """连续对话：第二轮请求必须带上第一轮的 user 与 assistant 消息。"""
    client = FakeClient([make_chunk("回复一")])
    messages = [
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "问题一"},
    ]
    create_completion(client, settings, messages)

    # 模拟主循环把回复写入历史后再问第二轮
    messages.append({"role": "assistant", "content": "回复一"})
    messages.append({"role": "user", "content": "问题二"})
    create_completion(client, settings, messages)

    second = client.chat.completions.calls[1]["messages"]
    roles = [m["role"] for m in second]
    assert roles == ["system", "user", "assistant", "user"]
    assert second[1]["content"] == "问题一"
    assert second[2]["content"] == "回复一"
