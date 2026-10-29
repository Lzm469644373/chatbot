"""命令行聊天机器人入口。

直接运行：

    python chat.py

支持连续对话（保留上下文）、流式输出，输入 exit / quit 退出。
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from openai import APIConnectionError, APIStatusError, AuthenticationError

from config import ConfigError, Settings, load_settings
from llm import build_client, create_completion, iter_delta_text

EXIT_WORDS = {"exit", "quit", ":q"}


def build_initial_messages(settings: Settings) -> list[dict[str, str]]:
    """对话初始只有一条 system 消息，它决定了助手的人设。"""
    return [{"role": "system", "content": settings.system_prompt}]


def trim_history(messages: list[dict[str, str]], max_messages: int) -> list[dict[str, str]]:
    """裁剪历史，但**永远保留 system 消息**。

    只保留最近的 ``max_messages - 1`` 条对话，避免上下文无限增长导致超长报错。
    """
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
    """主对话循环。

    ``input_fn`` / ``output_fn`` 可注入，便于自动化测试。
    返回进程退出码：0 正常退出，1 请求失败。
    """
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
            stream = create_completion(client, settings, messages)
        except AuthenticationError:
            output_fn("[错误] API Key 无效或已过期，请检查 CHATBOT_API_KEY。")
            messages.pop()  # 回滚这轮用户输入，保持上下文干净
            continue
        except APIConnectionError as exc:
            output_fn(f"[错误] 无法连接模型服务：{exc}")
            messages.pop()
            continue
        except APIStatusError as exc:
            output_fn(f"[错误] 服务返回异常：{exc.status_code} {exc.message}")
            messages.pop()
            continue

        # ---- 流式打印：先输出前缀，再边收边打，最后补一个换行 ----
        output_fn("Assistant: ", end="")
        collected: list[str] = []
        try:
            for piece in iter_delta_text(stream):
                collected.append(piece)
                output_fn(piece, end="", flush=True)
        except KeyboardInterrupt:
            output_fn("\n[已中断本次回复]")
        finally:
            # 无论成功还是中途中断，都只补一个换行，避免空行堆叠
            output_fn("")

        reply = "".join(collected)
        if reply:
            messages.append({"role": "assistant", "content": reply})


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"[配置错误] {exc}", file=sys.stderr)
        return 2

    print(settings)  # API Key 是 SecretStr，这里只会打印掩码

    try:
        client = build_client(settings)
    except ConfigError as exc:  # 缺少 API Key
        print(f"\n{exc}", file=sys.stderr)
        return 2

    return run_chat(client, settings)


if __name__ == "__main__":
    raise SystemExit(main())
