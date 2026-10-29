"""命令行聊天机器人入口（PR1：基础多轮对话，一次性输出）。"""

from __future__ import annotations

import sys
from collections.abc import Callable

from openai import APIConnectionError, APIStatusError, AuthenticationError

from config import ConfigError, Settings, load_settings
from llm import build_client, create_completion, extract_reply

EXIT_WORDS = {"exit", "quit", ":q"}


def build_initial_messages(settings: Settings) -> list[dict[str, str]]:
    """对话初始只有一条 system 消息。"""
    return [{"role": "system", "content": settings.system_prompt}]


def trim_history(messages: list[dict[str, str]], max_messages: int) -> list[dict[str, str]]:
    """裁剪历史，但永远保留 system 消息。"""
    if len(messages) <= max_messages:
        return messages

    system_messages = [m for m in messages if m["role"] == "system"]
    dialog = [m for m in messages if m["role"] != "system"]
    keep = max_messages - len(system_messages)
    return system_messages + dialog[-keep:]


def run_chat(
    client: object,
    settings: Settings,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[..., None] = print,
) -> int:
    """主对话循环。"""
    messages = build_initial_messages(settings)
    output_fn(f"已连接模型 {settings.model}（base_url={settings.base_url}）")
    output_fn("输入 exit / quit 退出。\n")

    while True:
        try:
            user_input = input_fn("You: ")
        except (EOFError, KeyboardInterrupt):
            output_fn("\n再见。")
            return 0

        user_input = user_input.strip()
        if not user_input:
            continue
        if user_input.lower() in EXIT_WORDS:
            output_fn("再见。")
            return 0

        messages.append({"role": "user", "content": user_input})
        messages = trim_history(messages, settings.max_history_messages)

        try:
            response = create_completion(client, settings, messages)
        except AuthenticationError:
            output_fn("[错误] API Key 无效或已过期，请检查 CHATBOT_API_KEY。")
            messages.pop()
            continue
        except APIConnectionError as exc:
            output_fn(f"[错误] 无法连接模型服务：{exc}")
            messages.pop()
            continue
        except APIStatusError as exc:
            output_fn(f"[错误] 服务返回异常：{exc.status_code} {exc.message}")
            messages.pop()
            continue

        reply = extract_reply(response)
        output_fn(f"Assistant: {reply}")
        if reply:
            messages.append({"role": "assistant", "content": reply})


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"[配置错误] {exc}", file=sys.stderr)
        return 2

    print(settings)

    try:
        client = build_client(settings)
    except ConfigError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2

    return run_chat(client, settings)


if __name__ == "__main__":
    raise SystemExit(main())
