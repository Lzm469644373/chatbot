"""集中式配置：所有可变参数都在这里，业务代码禁止硬编码。"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """聊天机器人配置，环境变量统一带 CHATBOT_ 前缀。"""

    model_config = SettingsConfigDict(
        env_prefix="CHATBOT_",
        env_file=".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    api_key: SecretStr | None = Field(default=None, description="API Key，打印时自动掩码")
    base_url: str = Field(default="https://api.deepseek.com", description="接口地址")
    model: str = Field(default="deepseek-chat", description="模型名称")

    temperature: float = Field(default=0.7, ge=0, le=2, description="采样温度 0~2")
    max_tokens: int | None = Field(default=None, gt=0, description="单次回复上限")

    system_prompt: str = Field(
        default="你是一个乐于助人的中文助手，回答简洁准确。",
        description="系统提示词",
    )
    max_history_messages: int = Field(
        default=20, ge=2, le=200, description="发送给模型的最大消息条数"
    )
    request_timeout: float = Field(default=60.0, gt=0, description="请求超时（秒）")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回全局唯一配置；测试里可 cache_clear() 后重读环境变量。"""
    return Settings()


class ConfigError(RuntimeError):
    """配置不合法。"""


def load_settings() -> Settings:
    """读取配置；校验失败时转成可读提示。"""
    try:
        return get_settings()
    except ValidationError as exc:
        lines = ["配置有误，请检查 .env 或环境变量："]
        for err in exc.errors():
            field = ".".join(str(p) for p in err["loc"]) or "(整体)"
            lines.append(f"  - {field}: {err['msg']}")
        raise ConfigError("\n".join(lines)) from exc


def require_api_key(settings: Settings) -> str:
    """取出明文 API Key；缺失时抛出带指引的异常。"""
    if settings.api_key is None or not settings.api_key.get_secret_value().strip():
        raise ConfigError(
            "未检测到 API Key。\n"
            "请把 .env.example 复制为 .env，并填入：\n"
            "  CHATBOT_API_KEY=sk-你的密钥\n"
            "也可以直接设置环境变量 CHATBOT_API_KEY。"
        )
    return settings.api_key.get_secret_value()
