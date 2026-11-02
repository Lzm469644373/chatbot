"""测试公共夹具：隔离环境变量与 .env 文件。"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from config import get_settings


@pytest.fixture(autouse=True)
def isolated_env(request, monkeypatch):
    """每个用例都在独立的临时目录里跑，并清空 CHATBOT_* 环境变量。

    这样用例之间互不影响，也不会误读项目目录下真实的 .env。
    """
    # 用 makedirs 而不是 tmp_path：mkdtemp 会创建受限 ACL 的目录，
    # 在某些受限运行环境（如沙箱）里会导致后续 scandir 被拒绝。
    safe_name = re.sub(r"[^\w.-]+", "_", request.node.name)
    workdir = Path(tempfile.gettempdir()) / "chatbot-tests" / safe_name
    workdir.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(workdir)
    for name in (
        "CHATBOT_API_KEY",
        "CHATBOT_BASE_URL",
        "CHATBOT_MODEL",
        "CHATBOT_TEMPERATURE",
        "CHATBOT_MAX_TOKENS",
        "CHATBOT_SYSTEM_PROMPT",
        "CHATBOT_MAX_HISTORY_MESSAGES",
        "CHATBOT_STREAM",
        "CHATBOT_REQUEST_TIMEOUT",
        "CHATBOT_SERVER_HOST",
        "CHATBOT_SERVER_PORT",
    ):
        monkeypatch.delenv(name, raising=False)

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------- FastAPI 测试夹具（离线，用假的模型客户端）----------


def make_chunk(text: str | None):
    """构造一个与 OpenAI 流式分片结构一致的对象。"""
    delta = SimpleNamespace(content=text)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


class FakeCompletions:
    """记录每次 create() 的入参，并按 stream 开关返回不同形态的响应。"""

    def __init__(self, owner: FakeClient) -> None:
        self._owner = owner

    def create(self, **kwargs):
        snapshot = dict(kwargs)
        # messages 必须深拷贝，否则后续会话追加会改到同一列表
        snapshot["messages"] = [dict(m) for m in kwargs["messages"]]
        self._owner.calls.append(snapshot)
        if kwargs.get("stream"):
            return iter([make_chunk(piece) for piece in self._owner.pieces])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._owner.reply))]
        )


class FakeClient:
    """假的 OpenAI 客户端：不联网，回复内容可预设。"""

    def __init__(self, reply: str = "这是测试回复。", pieces: list[str] | None = None):
        self.reply = reply
        self.pieces = list(pieces) if pieces is not None else [reply]
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=FakeCompletions(self))


@pytest.fixture
def settings(monkeypatch):
    """带假 Key 的配置对象，避免读到真实 .env。"""
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test")
    monkeypatch.setenv("CHATBOT_MODEL", "deepseek-chat")
    monkeypatch.setenv("CHATBOT_TEMPERATURE", "0.3")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def fake_client():
    return FakeClient()


@pytest.fixture
def api_app(settings, fake_client):
    """每个用例一个全新的 app：内存会话不会互相污染。"""
    from app.main import create_app
    from app.store import SessionStore

    return create_app(settings=settings, store=SessionStore(), client=fake_client)


@pytest.fixture
def api_client(api_app):
    from fastapi.testclient import TestClient

    with TestClient(api_app) as client:
        yield client
