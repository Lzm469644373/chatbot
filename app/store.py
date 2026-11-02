"""会话存储（内存实现）。

作业要求「会话先保存在内存中，读写操作集中放在一个模块，方便以后换成数据库」，
所以路由层不直接碰 dict，只通过这里的 SessionStore 增删查改。
换成 Redis / SQLite 时，只需要替换这个类的实现。
"""

from __future__ import annotations

from threading import RLock

Message = dict[str, str]


class SessionStore:
    """线程安全的内存会话表：``{session_id: [{"role": ..., "content": ...}]}``。

    FastAPI 的同步路由跑在线程池里，读写可能并发，所以统一加锁；
    对外返回的都是副本，避免调用方改到内部状态。
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[str, list[Message]] = {}

    def append(self, session_id: str, role: str, content: str) -> None:
        """追加一条消息；会话不存在时自动创建。"""
        with self._lock:
            self._sessions.setdefault(session_id, []).append(
                {"role": role, "content": content}
            )

    def extend(self, session_id: str, messages: list[Message]) -> None:
        """批量追加消息，便于把「用户 + 助手」一轮整体写入。"""
        with self._lock:
            bucket = self._sessions.setdefault(session_id, [])
            bucket.extend(dict(m) for m in messages)

    def get(self, session_id: str) -> list[Message] | None:
        """返回会话的消息副本；会话不存在时返回 ``None``。"""
        with self._lock:
            bucket = self._sessions.get(session_id)
            return None if bucket is None else [dict(m) for m in bucket]

    def list_ids(self) -> list[str]:
        """返回所有会话 ID（按首次出现的先后顺序）。"""
        with self._lock:
            return list(self._sessions)

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def delete(self, session_id: str) -> bool:
        """删除整个会话；返回是否真的删掉了。"""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)
