"""会话存储（SQLAlchemy ORM 实现）。

第四次作业这里直接用 sqlite3 写 SQL；本次改为 ORM：
- 会话与消息由 ``app.models`` 的 ``ChatSession`` / ``ChatMessage`` 映射；
- 每次操作用一个短生命周期 Session（``with`` 自动关闭），不再自己拼 SQL；
- 路由层只调用本类的接口，看不到任何 ORM 细节，以后换 PostgreSQL 只改引擎配置。

注意：表结构与第四次作业一致，旧的 ``chat.db`` 可以直接读取，不需要迁移。
"""

from __future__ import annotations

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.db import build_engine, build_session_factory, init_schema
from app.models import ChatMessage, ChatSession

Message = dict[str, str]


class SessionStore:
    """基于 SQLAlchemy ORM 的会话存储。

    每次读写都新开一个 Session 并在 ``with`` 结束时关闭；需要原子性的操作
    （写一轮对话）在同一个 Session 里 ``commit``，失败会整体回滚。
    """

    def __init__(self, db_path: str = "chat.db") -> None:
        self.db_path = db_path
        self.engine = build_engine(db_path)
        init_schema(self.engine)
        self._session_factory = build_session_factory(self.engine)

    # ---------- 生命周期 ----------

    def close(self) -> None:
        """释放连接池（服务关闭时调用；不会删除数据）。"""
        self.engine.dispose()

    def __enter__(self) -> SessionStore:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ---------- 写 ----------

    @staticmethod
    def _ensure_session(db: Session, session_id: str) -> None:
        """会话不存在时补一行，保证消息表的外键有父记录。"""
        if db.get(ChatSession, session_id) is None:
            db.add(ChatSession(id=session_id))

    def append(self, session_id: str, role: str, content: str) -> None:
        """追加一条消息；会话不存在时自动创建。"""
        with self._session_factory() as db:
            try:
                self._ensure_session(db, session_id)
                db.add(ChatMessage(session_id=session_id, role=role, content=content))
                db.commit()
            except Exception:
                db.rollback()
                raise

    def append_turn(
        self, session_id: str, user_content: str, assistant_content: str
    ) -> None:
        """把「用户提问 + 助手回复」放进同一个事务写入。

        两条消息在同一个 Session 里提交，任何一条失败都会整体回滚，
        不会留下「只有提问没有回复」的半轮对话。
        """
        with self._session_factory() as db:
            try:
                self._ensure_session(db, session_id)
                db.add_all(
                    [
                        ChatMessage(
                            session_id=session_id, role="user", content=user_content
                        ),
                        ChatMessage(
                            session_id=session_id,
                            role="assistant",
                            content=assistant_content,
                        ),
                    ]
                )
                db.commit()
            except Exception:
                db.rollback()
                raise

    def extend(self, session_id: str, messages: list[Message]) -> None:
        """批量追加消息（同一个事务）。"""
        with self._session_factory() as db:
            try:
                self._ensure_session(db, session_id)
                db.add_all(
                    [
                        ChatMessage(
                            session_id=session_id,
                            role=item["role"],
                            content=item["content"],
                        )
                        for item in messages
                    ]
                )
                db.commit()
            except Exception:
                db.rollback()
                raise

    def delete(self, session_id: str) -> bool:
        """删除整个会话；消息由外键级联删除。返回是否真的删掉了。"""
        with self._session_factory() as db:
            session = db.get(ChatSession, session_id)
            if session is None:
                return False
            db.delete(session)
            db.commit()
            return True

    def clear(self) -> None:
        """清空所有会话（消息级联删除）。"""
        with self._session_factory() as db:
            db.execute(delete(ChatSession))
            db.commit()

    # ---------- 读 ----------

    def get(self, session_id: str) -> list[Message] | None:
        """按对话顺序返回消息；会话不存在时返回 ``None``。"""
        with self._session_factory() as db:
            if db.get(ChatSession, session_id) is None:
                return None
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.id)
            )
            return [
                {"role": message.role, "content": message.content}
                for message in db.scalars(stmt)
            ]

    def list_ids(self) -> list[str]:
        """返回所有会话 ID（按创建顺序，用 rowid 保持与旧实现一致）。"""
        with self._session_factory() as db:
            stmt = select(ChatSession.id).order_by(text("sessions.rowid"))
            return list(db.scalars(stmt))

    def exists(self, session_id: str) -> bool:
        with self._session_factory() as db:
            return db.get(ChatSession, session_id) is not None

    def __len__(self) -> int:
        with self._session_factory() as db:
            total = db.scalar(select(func.count()).select_from(ChatSession))
            return int(total or 0)
