"""集中式配置：所有可变参数都在这里，业务代码禁止硬编码。

优先级（pydantic-settings 约定）：init 参数 > 环境变量 > .env 文件 > 字段默认值。
因此只需在 .env 里覆盖，无需改动代码。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """聊天机器人配置。

    所有字段都可以通过环境变量覆盖，环境变量统一带 ``CHATBOT_`` 前缀，
    例如 ``api_key`` 对应 ``CHATBOT_API_KEY``。
    """

    model_config = SettingsConfigDict(
        env_prefix="CHATBOT_",
        env_file=".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    # ---- 连接信息 ----
    api_key: SecretStr | None = Field(
        default=None,
        description="大模型服务的 API Key；用 SecretStr 包装，打印时不会泄露明文",
    )
    base_url: str = Field(
        default="https://api.deepseek.com",
        description="OpenAI 兼容的接口地址",
    )
    model: str = Field(default="deepseek-chat", description="模型名称")

    # ---- 生成参数 ----
    temperature: float = Field(
        default=0.7, ge=0, le=2, description="采样温度，必须在 0~2 之间"
    )
    max_tokens: int | None = Field(
        default=None, gt=0, description="单次回复的最大 token 数；None 表示用服务端默认值"
    )

    # ---- 对话行为 ----
    system_prompt: str = Field(
        default="你是一个乐于助人的中文助手，回答简洁准确。",
        description="系统提示词，决定助手的角色设定",
    )
    max_history_messages: int = Field(
        default=20,
        ge=2,
        le=200,
        description="发送给模型的最大消息条数（含 system），超出时裁剪最早的历史",
    )
    stream: bool = Field(default=True, description="是否启用流式输出")

    # ---- 网络 ----
    request_timeout: float = Field(
        default=60.0, gt=0, description="单次请求超时时间（秒）"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回全局唯一的配置实例。

    使用 ``lru_cache`` 而不是模块级单例，测试时可以用
    ``get_settings.cache_clear()`` 清空缓存后重新读取环境变量。
    """
    return Settings()


class ConfigError(RuntimeError):
    """配置不合法（例如环境变量取值越界）。"""


def load_settings() -> Settings:
    """读取配置；校验失败时转成可直接展示给用户的中文提示。"""
    try:
        return get_settings()
    except ValidationError as exc:  # 例如 CHATBOT_TEMPERATURE=5
        lines = ["配置有误，请检查 .env 或环境变量："]
        for err in exc.errors():
            field = ".".join(str(p) for p in err["loc"]) or "(整体)"
            lines.append(f"  - {field}: {err['msg']}")
        raise ConfigError("\n".join(lines)) from exc


def require_api_key(settings: Settings) -> str:
    """取出明文 API Key；缺失时抛出带操作指引的异常。"""
    if settings.api_key is None or not settings.api_key.get_secret_value().strip():
        raise ConfigError(
            "未检测到 API Key。\n"
            "请把 .env.example 复制为 .env，并填入：\n"
            "  CHATBOT_API_KEY=sk-你的密钥\n"
            "也可以直接设置环境变量 CHATBOT_API_KEY。"
        )
    return settings.api_key.get_secret_value()
