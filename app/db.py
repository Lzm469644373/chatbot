"""SQLAlchemy 引擎、Session 工厂与建表。

- ``build_engine``：按数据库路径创建 Engine，并给每个连接打开 SQLite 外键约束；
- ``build_session_factory``：生成 Session 工厂，store 的每次操作都从它开一个 Session；
- ``init_schema``：``create_all``，只补建缺失的表，绝不 DROP 或清空已有数据。
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base


def build_engine(db_path: str) -> Engine:
    """创建 SQLite Engine。

    ``:memory:`` 用 StaticPool 让所有 Session 共用同一个内存连接，
    否则每次连接都会拿到一个空库。
    """
    if db_path == ":memory:":
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        path = Path(db_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            f"sqlite:///{path.as_posix()}",
            connect_args={"check_same_thread": False},
        )

    # SQLite 默认不检查外键，必须每个连接显式打开，ON DELETE CASCADE 才会生效
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Session 工厂：每次数据库操作创建一个短生命周期 Session。"""
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def init_schema(engine: Engine) -> None:
    """建表；表已存在时跳过，不会影响已有聊天记录。"""
    Base.metadata.create_all(engine)
