@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title 聊天机器人 API 服务

echo ============================================
echo           聊天机器人 API 服务
echo ============================================
echo.

REM ---------- 1) 找一个装了 FastAPI 的 Python ----------
set "PY="
if exist "D:\conda\python.exe" (
    "D:\conda\python.exe" -c "import fastapi, uvicorn, openai" >nul 2>nul
    if !errorlevel! equ 0 set "PY=D:\conda\python.exe"
)
if not defined PY (
    python -c "import fastapi, uvicorn, openai" >nul 2>nul
    if !errorlevel! equ 0 set "PY=python"
)

if not defined PY (
    echo [错误] 没找到已安装依赖的 Python。
    echo        请先执行： pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM ---------- 2) 没有 .env 就生成并提示填写 ----------
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [提示] 已生成配置文件 .env，请把 CHATBOT_API_KEY 改成你自己的密钥。
    start notepad ".env"
    pause
    exit /b 0
)

REM ---------- 3) 启动 ----------
REM 监听地址与端口来自 config.py（CHATBOT_SERVER_HOST / CHATBOT_SERVER_PORT）
echo 正在启动服务，按 Ctrl+C 停止...
echo 启动后可在浏览器打开 http://127.0.0.1:8000/docs 查看接口文档
echo.
%PY% -m app

echo.
echo 服务已停止。
pause
