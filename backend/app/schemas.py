"""请求 / 响应模型：用 pydantic 做入参校验，保证空消息直接被拒绝。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """``POST /chat`` 与 ``POST /chat/stream`` 共用的请求体。"""

    session_id: str = Field(
        ...,
        description="调用方提供的会话 ID，第一次使用该 ID 时会自动创建会话",
        examples=["u1"],
    )
    message: str = Field(
        ...,
        description="用户消息，不能为空白",
        examples=["你好"],
    )

    @field_validator("session_id")
    @classmethod
    def session_id_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("session_id 不能为空")
        return value

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message 不能为空")
        return value


class ChatReply(BaseModel):
    """``POST /chat`` 的响应。"""

    session_id: str
    reply: str


class MessageOut(BaseModel):
    """历史记录中的一条消息。"""

    role: Literal["user", "assistant"]
    content: str


class SessionList(BaseModel):
    """``GET /sessions`` 的响应。"""

    sessions: list[str]


class SessionMessages(BaseModel):
    """``GET /sessions/{session_id}/messages`` 的响应。"""

    session_id: str
    messages: list[MessageOut]


class WordRequest(BaseModel):
    """``POST /study/word`` 的请求体。"""

    word: str = Field(
        ...,
        description="要讲解的英语单词",
        examples=["resilient"],
    )

    @field_validator("word")
    @classmethod
    def word_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("word 不能为空")
        return value


class WordReply(BaseModel):
    """``POST /study/word`` 的响应：释义 + 例句，由模型一次生成。"""

    word: str
    explanation: str
