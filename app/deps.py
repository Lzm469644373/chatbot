"""FastAPI 依赖：从 app.state 取配置 / 存储 / 模型客户端。

把依赖写成函数而不是模块级单例，测试时用 ``create_app(settings=..., client=...)``
注入假对象即可，不需要联网、也不读真实 .env。
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request

from app.store import SessionStore
from config import Settings
from llm import build_client


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> SessionStore:
    return request.app.state.store


def get_model_client(request: Request) -> Any:
    """懒加载模型客户端：只有真正调用对话接口时才需要 API Key。

    这样即使没配 Key，``import app.main`` 和 ``GET /health`` 也能正常工作，
    缺失 Key 的错误会在请求时以 503 返回。
    """
    state = request.app.state
    if state.client is None:
        state.client = build_client(state.settings)
    return state.client


SettingsDep = Annotated[Settings, Depends(get_settings)]
StoreDep = Annotated[SessionStore, Depends(get_store)]
ClientDep = Annotated[Any, Depends(get_model_client)]
