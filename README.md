# 命令行聊天机器人

用 Python + OpenAI SDK 写的命令行聊天机器人，支持连续多轮对话。
所有可变参数集中在 `config.py`，通过 `.env` 覆盖，代码中没有硬编码。

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env      # Windows: copy .env.example .env
# 编辑 .env，填写 CHATBOT_API_KEY
python chat.py
```

## 配置项

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CHATBOT_API_KEY` | 无（必填） | API Key，`SecretStr` 存储 |
| `CHATBOT_BASE_URL` | `https://api.deepseek.com` | 接口地址 |
| `CHATBOT_MODEL` | `deepseek-chat` | 模型名称 |
| `CHATBOT_TEMPERATURE` | `0.7` | 采样温度，0~2 |
| `CHATBOT_MAX_HISTORY_MESSAGES` | `20` | 最大消息条数 |
| `CHATBOT_REQUEST_TIMEOUT` | `60` | 请求超时（秒） |

## 目录结构

```
chatbot/
├── config.py      # 配置模型（pydantic-settings）
├── llm.py         # 模型调用封装
├── chat.py        # 命令行主循环
├── .env.example
└── requirements.txt
```
