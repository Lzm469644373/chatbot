"""测试公共夹具：隔离环境变量与 .env 文件。"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

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
    ):
        monkeypatch.delenv(name, raising=False)

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
