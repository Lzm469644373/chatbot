"""``python -m app``：读取 config.py 里的监听地址与端口后启动 uvicorn。"""

from __future__ import annotations

import uvicorn

from config import load_settings


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
    )


if __name__ == "__main__":
    main()
