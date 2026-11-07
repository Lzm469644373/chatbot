"""数据库存储层的离线测试：建表、历史连续、会话隔离、级联删除、持久化。

全部使用临时目录里的 SQLite 文件，不碰开发者本地的 chat.db，也不需要真实 Key。
"""

from __future__ import annotations

import sqlite3

from app.store import SessionStore


def test_tables_and_columns_are_created(tmp_path):
    """启动时自动建表：sessions + messages，字段与外键都要对得上。"""
    db_file = tmp_path / "schema.db"
    with SessionStore(str(db_file)):
        pass

    with sqlite3.connect(db_file) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"sessions", "messages"} <= tables

        message_columns = [
            row[1] for row in conn.execute("PRAGMA table_info(messages)")
        ]
        assert message_columns == ["id", "session_id", "role", "content", "created_at"]

        foreign_keys = list(conn.execute("PRAGMA foreign_key_list(messages)"))
        assert any(fk[2] == "sessions" for fk in foreign_keys)


def test_same_session_history_is_continuous(tmp_path):
    """同一会话按顺序返回，两轮对话不会乱序。"""
    with SessionStore(str(tmp_path / "history.db")) as store:
        store.append_turn("u1", "第一问", "第一答")
        store.append_turn("u1", "第二问", "第二答")

        assert store.get("u1") == [
            {"role": "user", "content": "第一问"},
            {"role": "assistant", "content": "第一答"},
            {"role": "user", "content": "第二问"},
            {"role": "assistant", "content": "第二答"},
        ]


def test_different_sessions_are_isolated(tmp_path):
    """不同会话互不干扰。"""
    with SessionStore(str(tmp_path / "isolate.db")) as store:
        store.append_turn("u1", "只属于 u1", "u1 的回答")
        store.append_turn("u2", "只属于 u2", "u2 的回答")

        assert [m["content"] for m in store.get("u1")] == ["只属于 u1", "u1 的回答"]
        assert [m["content"] for m in store.get("u2")] == ["只属于 u2", "u2 的回答"]
        assert store.list_ids() == ["u1", "u2"]


def test_delete_removes_messages_by_cascade(tmp_path):
    """删除会话后，消息表里的记录也要一起消失（外键级联）。"""
    db_file = tmp_path / "delete.db"
    with SessionStore(str(db_file)) as store:
        store.append_turn("u1", "会被删掉", "连同回答")
        assert store.delete("u1") is True
        assert store.get("u1") is None
        assert store.delete("u1") is False

    with sqlite3.connect(db_file) as conn:
        count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        assert count == 0


def test_data_survives_reopening_database(tmp_path):
    """持久化：关闭连接后重新打开，数据还在（模拟服务重启）。"""
    db_file = tmp_path / "persist.db"

    first = SessionStore(str(db_file))
    first.append_turn("u1", "记住我叫小明", "好的，小明")
    first.close()

    second = SessionStore(str(db_file))
    try:
        assert second.get("u1") == [
            {"role": "user", "content": "记住我叫小明"},
            {"role": "assistant", "content": "好的，小明"},
        ]
        assert second.list_ids() == ["u1"]
    finally:
        second.close()


def test_clear_removes_every_session(tmp_path):
    with SessionStore(str(tmp_path / "clear.db")) as store:
        store.append_turn("u1", "a", "b")
        store.append_turn("u2", "c", "d")
        assert len(store) == 2

        store.clear()

        assert store.list_ids() == []
        assert len(store) == 0
        assert store.get("u1") is None


def test_unknown_session_returns_none(tmp_path):
    with SessionStore(str(tmp_path / "unknown.db")) as store:
        assert store.get("nope") is None
        assert store.exists("nope") is False
        assert store.delete("nope") is False
