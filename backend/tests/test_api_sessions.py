"""会话管理接口的离线测试：列表、消息记录、清空、404。"""

from __future__ import annotations


def test_session_list_and_messages(api_client, fake_client):
    """新会话没出现时不返回；对话后能看到 ID 与有序的消息记录。"""
    assert api_client.get("/sessions").json() == {"sessions": []}

    api_client.post("/chat", json={"session_id": "u1", "message": "第一句"})

    assert api_client.get("/sessions").json() == {"sessions": ["u1"]}

    body = api_client.get("/sessions/u1/messages").json()
    assert body["session_id"] == "u1"
    assert body["messages"] == [
        {"role": "user", "content": "第一句"},
        {"role": "assistant", "content": fake_client.reply},
    ]


def test_delete_clears_session(api_client):
    """DELETE 之后会话消失，消息记录返回 404。"""
    api_client.post("/chat", json={"session_id": "u1", "message": "会被清掉"})

    response = api_client.delete("/sessions/u1")
    assert response.status_code == 204

    assert api_client.get("/sessions").json() == {"sessions": []}
    assert api_client.get("/sessions/u1/messages").status_code == 404


def test_unknown_session_returns_404(api_client):
    """查询 / 删除不存在的会话都返回 404。"""
    assert api_client.get("/sessions/not-exist/messages").status_code == 404
    assert api_client.delete("/sessions/not-exist").status_code == 404


def test_health_endpoint_works_without_api_key(api_client):
    """健康检查不调用模型，没配 Key 也应该正常。"""
    body = api_client.get("/health").json()
    assert body["status"] == "ok"
    assert body["model"] == "deepseek-chat"
