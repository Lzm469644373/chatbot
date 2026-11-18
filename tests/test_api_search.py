"""历史消息关键词查询的离线测试（ORM 查询表达式 + API 参数）。"""

from __future__ import annotations

REPLY = "这是测试回复。"


def seed(api_client, session_id: str, *messages: str) -> None:
    for message in messages:
        api_client.post("/chat", json={"session_id": session_id, "message": message})


def contents(response) -> list[str]:
    return [m["content"] for m in response.json()["messages"]]


def test_without_keyword_returns_full_history(api_client):
    seed(api_client, "u1", "我喜欢 Python", "今天天气不错")

    response = api_client.get("/sessions/u1/messages")

    assert response.status_code == 200
    assert contents(response) == [
        "我喜欢 Python",
        REPLY,
        "今天天气不错",
        REPLY,
    ]


def test_keyword_returns_only_matching_messages_in_order(api_client):
    seed(api_client, "u1", "第一条：关键词在这里", "第二条：无关内容", "第三条：又是关键词")

    response = api_client.get("/sessions/u1/messages", params={"keyword": "关键词"})

    assert response.status_code == 200
    assert contents(response) == [
        "第一条：关键词在这里",
        "第三条：又是关键词",
    ]


def test_keyword_only_searches_current_session(api_client):
    seed(api_client, "u1", "u1 也提到 Python")
    seed(api_client, "u2", "u2 的 Python 记录")

    u1_contents = contents(api_client.get("/sessions/u1/messages", params={"keyword": "Python"}))
    u2_contents = contents(api_client.get("/sessions/u2/messages", params={"keyword": "Python"}))

    assert u1_contents == ["u1 也提到 Python"]
    assert u2_contents == ["u2 的 Python 记录"]


def test_keyword_without_match_returns_empty_list(api_client):
    seed(api_client, "u1", "聊点别的")

    response = api_client.get("/sessions/u1/messages", params={"keyword": "不存在的词"})

    assert response.status_code == 200
    assert response.json() == {"session_id": "u1", "messages": []}


def test_blank_keyword_is_treated_as_no_filter(api_client):
    seed(api_client, "u1", "唯一一条")

    response = api_client.get("/sessions/u1/messages", params={"keyword": "   "})

    assert contents(response) == ["唯一一条", REPLY]


def test_keyword_on_unknown_session_returns_404(api_client):
    response = api_client.get("/sessions/nope/messages", params={"keyword": "Python"})
    assert response.status_code == 404
