"""对话接口：普通对话与流式对话。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.deps import ClientDep, SettingsDep, StoreDep
from app.schemas import ChatReply, ChatRequest
from app.service import chat_once, iter_reply, open_stream

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


@router.post(
    "/chat/stream",
    summary="流式对话（逐块返回纯文本，结束后写入历史）",
    response_class=StreamingResponse,
)
def chat_stream(
    payload: ChatRequest,
    settings: SettingsDep,
    store: StoreDep,
    client: ClientDep,
) -> StreamingResponse:
    stream = open_stream(client, settings, store, payload.session_id, payload.message)
    return StreamingResponse(
        iter_reply(stream, store, payload.session_id),
        media_type="text/plain; charset=utf-8",
    )
