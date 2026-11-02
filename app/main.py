"""FastAPI 应用入口。

本地启动：``python -m app``（读取 config.py 里的 host / port），
或用 uvicorn 直接跑：``uvicorn app.main:app --reload``。
"""

from __future__ import annotations

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
    就能在完全离线、没有真实 Key 的情况下跑通所有接口。
    """
    app_settings = settings or load_settings()
    app = FastAPI(
        title="聊天机器人 API",
        version="1.0.0",
        description=(
            "把命令行聊天机器人改造成 HTTP 服务："
            "连续对话、内存会话管理、流式输出。"
        ),
    )
    app.state.settings = app_settings
    app.state.store = store or SessionStore()
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
