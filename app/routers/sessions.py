"""会话管理接口：列表、消息记录、清空。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from app.deps import StoreDep
from app.schemas import MessageOut, SessionList, SessionMessages

router = APIRouter(prefix="/sessions", tags=["会话"])


@router.get("", response_model=SessionList, summary="查看所有会话 ID")
def list_sessions(store: StoreDep) -> SessionList:
    return SessionList(sessions=store.list_ids())


@router.get(
    "/{session_id}/messages",
    response_model=SessionMessages,
    summary="查看某个会话的消息记录",
)
def get_session_messages(session_id: str, store: StoreDep) -> SessionMessages:
    messages = store.get(session_id)
    if messages is None:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    return SessionMessages(
        session_id=session_id,
        messages=[MessageOut(**m) for m in messages],
    )


@router.delete(
    "/{session_id}",
    status_code=204,
    summary="清空某个会话（删除后该 ID 视为新会话）",
)
def delete_session(session_id: str, store: StoreDep) -> Response:
    if not store.delete(session_id):
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    return Response(status_code=204)
