"""学习功能接口：单词讲解。"""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import ClientDep, SettingsDep
from app.schemas import WordReply, WordRequest
from app.service import explain_word

router = APIRouter(prefix="/study", tags=["学习功能"])


@router.post(
    "/word",
    response_model=WordReply,
    summary="单词讲解：给出词性、中文释义与一个例句",
)
def explain(
    payload: WordRequest,
    settings: SettingsDep,
    client: ClientDep,
) -> WordReply:
    explanation = explain_word(client, settings, payload.word)
    return WordReply(word=payload.word, explanation=explanation)
