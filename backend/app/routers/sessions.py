"""会话管理接口：列表、消息记录（支持关键词过滤）、清空。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response

from app.deps import StoreDep
from app.schemas import MessageOut, SessionList, SessionMessages

router = APIRouter(prefix="/sessions", tags=["会话"])


@router.get("", response_model=SessionList, summary="查看所有会话 ID")
def list_sessions(store: StoreDep) -> SessionList:
    return SessionList(sessions=store.list_ids())


@router.get(
    "/{session_id}/messages",
    response_model=SessionMessages,
    summary="查看某个会话的消息记录（可选按关键词过滤）",
)
def get_session_messages(
    session_id: str,
    store: StoreDep,
    keyword: Annotated[
        str | None,
        Query(
            description="只返回当前会话中内容包含该关键词的消息；不传返回完整历史",
            examples=["Python"],
        ),
    ] = None,
) -> SessionMessages:
    # 空白关键词等同于不传，避免出现「传入空串却查不到任何消息」的歧义
    normalized = keyword.strip() if keyword else None
    messages = store.get(session_id, keyword=normalized or None)
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
