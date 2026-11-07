"""FastAPI 应用入口。

本地启动：``python -m app``（读取 config.py 里的 host / port），
或用 uvicorn 直接跑：``uvicorn app.main:app --reload``。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from openai import APIError

from app.routers import chat, sessions, study
from app.store import SessionStore
from config import ConfigError, Settings, load_settings


def create_app(
    *,
    settings: Settings | None = None,
    store: SessionStore | None = None,
    client: object | None = None,
) -> FastAPI:
    """构造应用。

    ``settings`` / ``store`` / ``client`` 都可以注入，测试时传入假对象，
    就能在完全离线、没有真实 Key、也不碰真实数据库的情况下跑通所有接口。
    """
    app_settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 启动时按配置打开 SQLite 并自动建表；不传 store 时在这里创建，
        # 这样 import app.main 本身不会产生数据库文件。
        store_instance = app.state.store
        if store_instance is None:
            store_instance = SessionStore(app_settings.db_path)
            app.state.store = store_instance
        yield
        store_instance.close()

    app = FastAPI(
        title="聊天机器人 API",
        version="2.0.0",
        description=(
            "聊天机器人 HTTP 服务：连续对话、SQLite 会话持久化、"
            "流式输出，以及由后端托管的网页聊天界面。"
        ),
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.store = store
    app.state.client = client

    @app.exception_handler(ConfigError)
    async def handle_config_error(_request, exc: ConfigError) -> JSONResponse:
        # 没配 Key / 配置越界时给出可读提示，而不是 500 栈
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(APIError)
    async def handle_upstream_error(_request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=502, content={"detail": f"模型服务调用失败：{exc}"}
        )

    app.include_router(chat.router)
    app.include_router(sessions.router)
    app.include_router(study.router)

    @app.get("/health", tags=["运维"], summary="健康检查（不调用模型）")
    def health() -> dict[str, str]:
        return {"status": "ok", "model": app_settings.model}

    return app


app = create_app()
