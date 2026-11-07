"""会话存储（SQLite 实现）。

第三次作业这里是内存字典，现在改成 SQLite：服务重启后会话与消息仍然存在。
路由层只调用本类的接口，不写 SQL，方便以后把 SQLite 换成 MySQL / PostgreSQL。

表结构见 ``app/db.py``：``sessions``（会话）与 ``messages``（消息，外键指向会话）。
"""

from __future__ import annotations

from threading import RLock

from app.db import connect, init_schema

Message = dict[str, str]


class SessionStore:
    """基于 SQLite 的会话存储。

    一个实例持有一个连接（``check_same_thread=False``），所有读写都用
    ``RLock`` 串行化：FastAPI 的同步路由在线程池里并发执行，SQLite 写操作
    本身也不允许同时进行。
    """

    def __init__(self, db_path: str = "chat.db") -> None:
        self.db_path = db_path
        self._lock = RLock()
        self._conn = connect(db_path)
        init_schema(self._conn)

    # ---------- 生命周期 ----------

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> SessionStore:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ---------- 写 ----------

    def _ensure_session(self, session_id: str) -> None:
        """会话不存在时补一行，保证消息表的外键有父记录。"""
        self._conn.execute(
            "INSERT OR IGNORE INTO sessions (id) VALUES (?)", (session_id,)
        )

    def append(self, session_id: str, role: str, content: str) -> None:
        """追加一条消息；会话不存在时自动创建。"""
        with self._lock:
            self._ensure_session(session_id)
            self._conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            self._conn.commit()

    def append_turn(
        self, session_id: str, user_content: str, assistant_content: str
    ) -> None:
        """把「用户提问 + 助手回复」作为一轮原子写入（同一个事务）。

        分两次写的话，并发请求可能读到「只有提问没有回复」的半截历史。
        """
        with self._lock:
            self._ensure_session(session_id)
            self._conn.executemany(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                [
                    (session_id, "user", user_content),
                    (session_id, "assistant", assistant_content),
                ],
            )
            self._conn.commit()

    def extend(self, session_id: str, messages: list[Message]) -> None:
        """批量追加消息。"""
        with self._lock:
            self._ensure_session(session_id)
            self._conn.executemany(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                [(session_id, m["role"], m["content"]) for m in messages],
            )
            self._conn.commit()

    def delete(self, session_id: str) -> bool:
        """删除整个会话；消息由外键级联删除。返回是否真的删掉了。"""
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM sessions WHERE id = ?", (session_id,)
            )
            self._conn.commit()
            return cursor.rowcount > 0

    def clear(self) -> None:
        """清空所有会话（消息级联删除）。"""
        with self._lock:
            self._conn.execute("DELETE FROM sessions")
            self._conn.commit()

    # ---------- 读 ----------

    def get(self, session_id: str) -> list[Message] | None:
        """按对话顺序返回消息；会话不存在时返回 ``None``。"""
        with self._lock:
            exists = self._conn.execute(
                "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if exists is None:
                return None
            rows = self._conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
            return [{"role": row["role"], "content": row["content"]} for row in rows]

    def list_ids(self) -> list[str]:
        """返回所有会话 ID（按创建顺序）。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id FROM sessions ORDER BY rowid"
            ).fetchall()
            return [row["id"] for row in rows]

    def exists(self, session_id: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            return row is not None

    def __len__(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()
            return int(row["n"])
