"""对话接口的离线测试：连续对话、会话隔离、空消息校验。

用 TestClient 打真实 HTTP 路径，模型客户端由 conftest 里的假对象注入，
因此不联网、不需要真实 API Key。
"""

from __future__ import annotations


def test_same_session_keeps_history(api_client, fake_client):
    """同一 session_id 的第二轮请求，必须带上第一轮的 user 与 assistant。"""
    first = api_client.post("/chat", json={"session_id": "u1", "message": "我叫小明"})
    assert first.status_code == 200
    assert first.json() == {"session_id": "u1", "reply": fake_client.reply}

    second = api_client.post("/chat", json={"session_id": "u1", "message": "我叫什么？"})
    assert second.status_code == 200

    sent = fake_client.calls[-1]["messages"]
    assert sent[0]["role"] == "system"
    assert sent[-1] == {"role": "user", "content": "我叫什么？"}
    assert {"role": "user", "content": "我叫小明"} in sent
    assert {"role": "assistant", "content": fake_client.reply} in sent


def test_different_sessions_do_not_mix(api_client, fake_client):
    """两个会话的历史不能串在一起。"""
    api_client.post("/chat", json={"session_id": "u1", "message": "只属于 u1 的秘密"})
    api_client.post("/chat", json={"session_id": "u2", "message": "只属于 u2 的秘密"})

    sent_for_u2 = fake_client.calls[-1]["messages"]
    contents = [m["content"] for m in sent_for_u2]
    assert "只属于 u1 的秘密" not in contents
    assert "只属于 u2 的秘密" in contents


def test_empty_message_is_rejected(api_client):
    """空消息 / 空白 session_id / 缺字段都要被入参校验拒绝（4xx）。"""
    bad_payloads = [
        {"session_id": "u1", "message": ""},
        {"session_id": "u1", "message": "   "},
        {"session_id": "   ", "message": "你好"},
        {"message": "你好"},
    ]
    for payload in bad_payloads:
        response = api_client.post("/chat", json=payload)
        assert response.status_code == 422, payload


def test_study_word_endpoint(api_client, fake_client):
    """学习功能可通过 API 调用：返回释义，且用的是专属 system 提示词。"""
    fake_client.reply = "resilient：形容词，有韧性的。例句：She is resilient. 她很有韧性。"
    response = api_client.post("/study/word", json={"word": "resilient"})

    assert response.status_code == 200
    assert response.json() == {
        "word": "resilient",
        "explanation": fake_client.reply,
    }

    call = fake_client.calls[-1]
    assert call["stream"] is False
    assert call["messages"][0]["role"] == "system"
    assert "英语" in call["messages"][0]["content"]
    assert call["messages"][-1] == {"role": "user", "content": "单词：resilient"}


def test_study_word_rejects_blank_word(api_client):
    for payload in ({"word": ""}, {"word": "   "}, {}):
        assert api_client.post("/study/word", json=payload).status_code == 422
