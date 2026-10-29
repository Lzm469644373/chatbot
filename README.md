# 命令行聊天机器人

一个用 Python 写的命令行聊天机器人，支持**连续对话**（记住上下文）和**流式输出**（边生成边打印）。
所有可变参数集中在 `config.py`，通过 `.env` 覆盖，代码里没有硬编码。

## 功能

- **连续对话**：每轮把历史消息一起发给模型；历史过长时按 `CHATBOT_MAX_HISTORY_MESSAGES` 裁剪，但**始终保留 system 提示词**。
- **流式输出**：`stream=True`，收到一个分片就打印一个分片，不会等整段生成完。
- **配置集中管理**：`config.py` + `pydantic-settings`，支持 `.env` 与环境变量；`api_key` 用 `SecretStr` 包装，`print(settings)` 只显示 `**********`。
- **友好的错误提示**：缺少 Key、Key 无效、网络不通、参数越界都会给出中文说明而不是抛栈。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 准备配置
cp .env.example .env      # Windows: copy .env.example .env
# 编辑 .env，至少填写 CHATBOT_API_KEY

# 3. 运行
python chat.py
```

运行后：

```
You: 你好，我叫小明
Assistant: 你好，小明！有什么可以帮你的吗？
You: 我叫什么名字？
Assistant: 你叫小明。
You: exit
再见。
```

## 配置项

全部配置位于 `config.py` 的 `Settings`，环境变量统一带 `CHATBOT_` 前缀。

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CHATBOT_API_KEY` | 无（必填） | API Key，`SecretStr` 存储 |
| `CHATBOT_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容接口地址 |
| `CHATBOT_MODEL` | `deepseek-chat` | 模型名称 |
| `CHATBOT_TEMPERATURE` | `0.7` | 采样温度，必须在 0~2 之间 |
| `CHATBOT_MAX_TOKENS` | 空 | 单次回复上限，空表示用服务端默认 |
| `CHATBOT_SYSTEM_PROMPT` | 内置提示词 | 助手人设 |
| `CHATBOT_MAX_HISTORY_MESSAGES` | `20` | 发送给模型的最大条数（含 system） |
| `CHATBOT_STREAM` | `true` | 是否流式输出 |
| `CHATBOT_REQUEST_TIMEOUT` | `60` | 请求超时（秒） |

优先级：命令行参数 > 环境变量 > `.env` > 字段默认值。

## 项目结构

```
chatbot/
├── config.py          # 配置模型 + get_settings()（lru_cache）
├── llm.py             # 构造客户端 / 发起请求 / 解析流式分片
├── chat.py            # 命令行主循环
├── tests/
│   ├── conftest.py    # 隔离环境变量与 .env
│   ├── test_config.py # 配置解析、越界校验、SecretStr 掩码
│   └── test_llm.py    # mock client，断言传参
├── .env.example
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

## 测试

测试完全离线，不需要真实 API Key，也不会发起网络请求：

```bash
pytest
```

覆盖点：

| 文件 | 测什么 |
| --- | --- |
| `tests/test_config.py` | 默认值正确、环境变量覆盖、`CHATBOT_TEMPERATURE=5` 抛 `ValidationError`、`SecretStr` 不泄露明文 |
| `tests/test_llm.py` | mock client 后断言 `model` / `temperature` / `messages` 结构 / `stream=True`；多轮对话上下文累积；空分片跳过 |

用 `monkeypatch.setenv` 造环境，配合 `get_settings()` 的 `lru_cache`（测试里 `cache_clear()`），因此不存在测不了的模块级单例。

## 设计要点

1. **为什么把 `create_completion` 单独抽出来**：测试里可以直接塞一个假 client，断言传参，而不必真的联网。
2. **为什么用 `get_settings()` 而不是模块级 `settings = Settings()`**：模块级单例一旦在 import 时求值，测试就没法改环境变量；用函数 + `lru_cache` 兼顾「全局唯一」和「可测试」。
3. **历史裁剪为什么不能简单切片**：`messages[0]` 是 system 提示词，简单 `messages[-N:]` 会把它丢掉，导致人设失效。`trim_history` 单独保留所有 system 消息。
4. **流式打印为什么不会多空行**：前缀只打印一次，分片用 `end=""` 拼接，循环结束后统一补一个换行。

## 开发流程

仓库采用功能分支 + PR 的方式迭代：

- `main`：受保护分支，禁止直接 push
- `feat/config-and-chat`：配置模块 + 基础多轮对话
- `feat/stream-and-tests`：流式输出 + 两个单元测试

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat: 新增流式输出
fix: 修正历史裁剪时误删 system prompt
test: 新增配置校验测试
docs: 补充 .env 配置说明
```
