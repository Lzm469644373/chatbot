"""流式接口的离线测试：必须传 stream=True、内容正确、结束后写入历史。"""

from __future__ import annotations


def test_stream_returns_text_and_requests_stream(api_client, fake_client):
    """响应是逐块文本，且调用模型时必须 stream=True。"""
    fake_client.reply = "你好，世界"
    fake_client.pieces = ["你好", "，", "世界"]

    response = api_client.post(
        "/chat/stream", json={"session_id": "s1", "message": "打个招呼"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "你好，世界"
    assert fake_client.calls[-1]["stream"] is True


def test_stream_saves_full_reply_to_history(api_client, fake_client):
    """流式结束后，完整回复必须写进该会话的历史记录。"""
    fake_client.reply = "第一段第二段"
    fake_client.pieces = ["第一段", "第二段"]

    api_client.post("/chat/stream", json={"session_id": "s1", "message": "请分段说"})

    body = api_client.get("/sessions/s1/messages").json()
    assert body["messages"] == [
        {"role": "user", "content": "请分段说"},
        {"role": "assistant", "content": "第一段第二段"},
    ]


def test_stream_keeps_previous_context(api_client, fake_client):
    """流式请求也要带上同一会话里之前的对话。"""
    api_client.post("/chat", json={"session_id": "s1", "message": "我叫小明"})

    fake_client.reply = "好的"
    fake_client.pieces = ["好的"]
    api_client.post("/chat/stream", json={"session_id": "s1", "message": "我叫什么？"})

    sent = fake_client.calls[-1]["messages"]
    assert {"role": "user", "content": "我叫小明"} in sent
    assert sent[-1] == {"role": "user", "content": "我叫什么？"}
    assert fake_client.calls[-1]["stream"] is True


def test_stream_rejects_empty_message(api_client):
    response = api_client.post(
        "/chat/stream", json={"session_id": "s1", "message": "   "}
    )
    assert response.status_code == 422
