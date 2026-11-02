"""对话接口。"""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import ClientDep, SettingsDep, StoreDep
from app.schemas import ChatReply, ChatRequest
from app.service import chat_once

router = APIRouter(tags=["对话"])


@router.post("/chat", response_model=ChatReply, summary="普通对话（一次性返回完整回复）")
def chat(
    payload: ChatRequest,
    settings: SettingsDep,
    store: StoreDep,
    client: ClientDep,
) -> ChatReply:
    reply = chat_once(client, settings, store, payload.session_id, payload.message)
    return ChatReply(session_id=payload.session_id, reply=reply)
