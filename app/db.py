"""SQLite 连接与建表语句。

把「怎么连库」和「表结构」集中在这里，``app/store.py`` 只负责业务语义的
增删查改。以后换成 MySQL / PostgreSQL 时，替换这个模块和 store 里的 SQL 即可，
路由层完全不用动。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# 两张表：会话表 + 消息表，消息通过外键指向会话。
# README 里的 mermaid ER 图必须和这里的字段、类型、主外键保持一致。
SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
"""


def connect(db_path: str) -> sqlite3.Connection:
    """打开数据库连接；文件不存在时 SQLite 会自动创建。

    ``check_same_thread=False`` 配合 store 里的锁使用：FastAPI 的同步路由
    跑在线程池里，同一个连接会被不同线程访问。
    """
    if db_path != ":memory:":
        Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # SQLite 默认不检查外键，必须显式打开，ON DELETE CASCADE 才会生效
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """建表 + 建索引；已存在时不会重复创建（启动时自动执行）。"""
    conn.executescript(SCHEMA)
    conn.commit()
