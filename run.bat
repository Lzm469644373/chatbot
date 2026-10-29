@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title 命令行聊天机器人

echo ============================================
echo             命令行聊天机器人
echo ============================================
echo.

REM ---------- 0) 本地依赖目录（可选，用于免安装场景）----------
set "PYLIB=%~dp0..\_pylibs"
if exist "%PYLIB%\openai" set "PYTHONPATH=%PYLIB%;%PYTHONPATH%"

REM ---------- 1) 找一个装了依赖的 Python ----------
set "PY="
if exist "D:\conda\python.exe" (
    "D:\conda\python.exe" -c "import openai, pydantic_settings" >nul 2>nul
    if !errorlevel! equ 0 set "PY=D:\conda\python.exe"
)
if not defined PY (
    python -c "import openai, pydantic_settings" >nul 2>nul
    if !errorlevel! equ 0 set "PY=python"
)
if not defined PY (
    py -3 -c "import openai, pydantic_settings" >nul 2>nul
    if !errorlevel! equ 0 set "PY=py -3"
)

REM ---------- 2) 找不到就尝试安装依赖 ----------
if not defined PY (
    echo [提示] 正在尝试安装依赖，请稍候...
    python --version >nul 2>nul
    if !errorlevel! equ 0 (
        python -m pip install -r requirements.txt
        if !errorlevel! equ 0 (
            set "PY=python"
        )
    )
)

if not defined PY (
    echo.
    echo [错误] 没能准备好 Python 环境。
    echo        请确认已安装 Python 3.10+（安装时勾选 Add Python to PATH），
    echo        然后在本目录执行： pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM ---------- 3) 没有 .env 就生成并提示填写 ----------
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [提示] 已生成配置文件 .env，请把 CHATBOT_API_KEY 改成你自己的密钥。
    echo        记事本打开后填好保存，再重新双击本脚本。
    echo.
    start notepad ".env"
    pause
    exit /b 0
)

REM ---------- 4) 密钥仍是占位符 ----------
findstr /C:"CHATBOT_API_KEY=sk-xxxx" ".env" >nul 2>nul
if !errorlevel! equ 0 (
    echo [提示] .env 里的 API Key 还是占位符，请先填真实密钥。
    start notepad ".env"
    pause
    exit /b 0
)

REM ---------- 5) 启动 ----------
echo 正在启动...（输入 exit 或 quit 退出）
echo.
%PY% chat.py

echo.
echo 程序已退出。
pause
