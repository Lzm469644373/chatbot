"""SQLAlchemy 2.x ORM 模型：会话表与消息表。

表名、字段、主外键和第四次作业的建表语句保持一致，所以旧的 ``chat.db``
可以直接打开读取，不需要迁移；``create_all`` 只会补建缺失的表，不会删除或清空数据。
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


class ChatSession(Base):
    """会话：对应 ``sessions`` 表。"""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )

    # 一个会话包含多条消息；删除会话时由数据库外键级联删除消息
    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
        passive_deletes=True,
    )


class ChatMessage(Base):
    """消息：对应 ``messages`` 表，``session_id`` 外键指向 ``sessions.id``。"""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        Index("idx_messages_session", "session_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")
