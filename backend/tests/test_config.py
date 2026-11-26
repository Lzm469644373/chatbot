"""配置解析的单元测试（离线，不需要真实 API Key）。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from config import Settings, get_settings


def test_defaults_are_stable(monkeypatch):
    """只给 api_key，其余字段应取 config.py 里的默认值。"""
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test")

    settings = get_settings()

    assert settings.base_url == "https://api.deepseek.com"
    assert settings.model == "deepseek-chat"
    assert settings.temperature == 0.7
    assert settings.max_history_messages == 20
    assert settings.stream is True
    assert settings.request_timeout == 60.0


def test_env_variables_override_defaults(monkeypatch):
    """环境变量应覆盖默认值。"""
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test")
    monkeypatch.setenv("CHATBOT_MODEL", "deepseek-reasoner")
    monkeypatch.setenv("CHATBOT_TEMPERATURE", "0.2")

    settings = get_settings()

    assert settings.model == "deepseek-reasoner"
    assert settings.temperature == 0.2


def test_temperature_out_of_range_raises(monkeypatch):
    """CHATBOT_TEMPERATURE=5 超出 0~2，必须抛 ValidationError。"""
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test")
    monkeypatch.setenv("CHATBOT_TEMPERATURE", "5")

    with pytest.raises(ValidationError) as excinfo:
        Settings()

    assert "temperature" in str(excinfo.value)


def test_secret_str_is_masked(monkeypatch):
    """api_key 使用 SecretStr，print / repr 都不能出现明文。"""
    secret = "sk-super-secret-value-1234567890"
    monkeypatch.setenv("CHATBOT_API_KEY", secret)

    settings = get_settings()

    # 打印与对象表示都不应泄露
    assert secret not in str(settings)
    assert secret not in repr(settings)
    assert "**********" in str(settings)

    # 但业务代码仍能取到明文
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == secret


def test_missing_api_key_does_not_crash_parsing():
    """缺少 api_key 时配置对象仍可构造，由上层给出可读提示。"""
    settings = Settings()

    assert settings.api_key is None
