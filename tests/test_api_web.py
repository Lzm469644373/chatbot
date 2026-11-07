"""网页托管的离线测试：根路径返回 index.html、页面不泄露 Key、挂载不吞接口。"""

from __future__ import annotations


def test_index_page_is_served(api_client):
    """GET / 应该返回后端托管的聊天页面，而不是 404。"""
    response = api_client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    body = response.text
    assert "<!doctype html>" in body.lower()
    assert "聊天机器人" in body
    assert "/chat/stream" in body


def test_static_index_file_is_served(api_client):
    assert api_client.get("/index.html").status_code == 200


def test_page_does_not_expose_api_key(api_client):
    """页面是纯静态文件，不能出现任何密钥。"""
    body = api_client.get("/").text

    assert "sk-test" not in body
    assert "CHATBOT_API_KEY" not in body


def test_static_mount_does_not_shadow_api(api_client):
    """挂载静态目录后，/chat、/sessions、/docs 仍然正常。"""
    response = api_client.post("/chat", json={"session_id": "w1", "message": "你好"})

    assert response.status_code == 200
    assert api_client.get("/sessions").json() == {"sessions": ["w1"]}
    assert api_client.get("/docs").status_code == 200
