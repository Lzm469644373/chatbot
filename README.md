# 聊天机器人（命令行 + FastAPI 服务）

把上一个作业的命令行聊天机器人改造成 **FastAPI HTTP 服务**：调用方通过 `session_id`
发起连续对话，会话保存在内存中，并提供会话列表 / 消息记录 / 清空接口。
原有的命令行入口 `chat.py` 仍然可用，两者共用同一套配置与模型调用封装。

## 功能

- **HTTP 对话**：`POST /chat`，同一 `session_id` 自动带上历史，不同会话互不串话。
- **会话管理**：`GET /sessions`、`GET /sessions/{id}/messages`、`DELETE /sessions/{id}`。
- **配置集中管理**：`config.py` + `pydantic-settings`，`.env` 覆盖，业务代码无硬编码；
  `api_key` 用 `SecretStr` 包装，接口响应里不会出现密钥。
- **错误处理**：空消息 422、不存在的会话 404、没配 Key 503、模型服务异常 502。
- **离线测试**：pytest + FastAPI `TestClient`，模型客户端用假对象注入，不联网。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 准备配置
cp .env.example .env          # Windows: copy .env.example .env
# 编辑 .env，至少填写 CHATBOT_API_KEY

# 3. 启动服务（监听地址与端口来自 config.py）
python -m app
# 或：uvicorn app.main:app --reload
```

启动后打开 <http://127.0.0.1:8000/docs> 可以看到自动生成的接口文档（Swagger UI）。
Windows 也可以直接双击 `run_server.bat`。

命令行版本仍然可以运行：

```bash
python chat.py
```

## 接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/chat` | 普通对话，一次性返回完整回复 |
| `GET` | `/sessions` | 查看所有会话 ID |
| `GET` | `/sessions/{session_id}/messages` | 查看某个会话的消息记录 |
| `DELETE` | `/sessions/{session_id}` | 清空某个会话 |
| `GET` | `/health` | 健康检查（不调用模型） |

### 对话

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"u1","message":"你好，我叫小明"}'
```

```json
{"session_id": "u1", "reply": "你好，小明！有什么可以帮你的吗？"}
```

再问一轮，历史会自动带上：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"u1","message":"我叫什么名字？"}'
```

### 会话管理

```bash
curl http://127.0.0.1:8000/sessions
# {"sessions": ["u1"]}

curl http://127.0.0.1:8000/sessions/u1/messages
# {"session_id":"u1","messages":[{"role":"user","content":"你好，我叫小明"},
#                               {"role":"assistant","content":"你好，小明！..."}]}

curl -X DELETE http://127.0.0.1:8000/sessions/u1
# 204 No Content；之后再查该会话返回 404
```

### 错误约定

| 情况 | 状态码 |
| --- | --- |
| `message` 为空 / 全空白，或缺少字段 | `422` |
| `session_id` 为空 / 全空白 | `422` |
| 查询或删除不存在的会话 | `404` |
| 没有配置 `CHATBOT_API_KEY` | `503` |
| 模型服务连接失败 / 返回错误 | `502` |

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
| `CHATBOT_STREAM` | `true` | 命令行模式是否流式输出 |
| `CHATBOT_REQUEST_TIMEOUT` | `60` | 请求超时（秒） |
| `CHATBOT_SERVER_HOST` | `127.0.0.1` | HTTP 服务监听地址 |
| `CHATBOT_SERVER_PORT` | `8000` | HTTP 服务监听端口 |

优先级：环境变量 > `.env` > 字段默认值。

## 项目结构

```
chatbot/
├── app/                    # FastAPI 服务
│   ├── main.py             # create_app()：装配路由、异常处理、/health
│   ├── deps.py             # 依赖注入：配置 / 会话存储 / 模型客户端
│   ├── schemas.py          # 请求与响应模型（空消息在这里被拒绝）
│   ├── store.py            # 内存会话存储（以后换数据库只改这里）
│   ├── service.py          # 业务逻辑：取历史 → 调模型 → 写历史
│   ├── routers/
│   │   ├── chat.py         # POST /chat
│   │   └── sessions.py     # 会话管理接口
│   └── __main__.py         # python -m app
├── config.py               # 配置模型 + get_settings()（lru_cache）
├── conversation.py         # system 消息、历史裁剪（CLI 与 API 共用）
├── llm.py                  # 构造客户端 / 发起请求 / 解析响应
├── chat.py                 # 命令行主循环
├── tests/
│   ├── conftest.py         # 隔离环境变量 + 假客户端与 app 夹具
│   ├── test_config.py      # 配置解析、越界校验、SecretStr 掩码
│   ├── test_llm.py         # mock client，断言传参
│   ├── test_api_chat.py    # 连续对话、会话隔离、空消息
│   └── test_api_sessions.py# 会话列表、消息记录、清空、404
├── docs/                   # 运行与测试证据
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── run.bat                 # 一键启动命令行版
└── run_server.bat          # 一键启动 API 服务
```

## 测试

测试完全离线，不需要真实 API Key，也不会发起网络请求：

```bash
pytest
```

| 文件 | 测什么 |
| --- | --- |
| `tests/test_config.py` | 默认值正确、环境变量覆盖、`CHATBOT_TEMPERATURE=5` 抛 `ValidationError`、`SecretStr` 不泄露明文 |
| `tests/test_llm.py` | mock client 后断言 `model` / `temperature` / `messages` / `stream=True` |
| `tests/test_api_chat.py` | 同一会话能连续对话、不同会话历史互不混用、空消息被拒绝 |
| `tests/test_api_sessions.py` | 能查看会话列表与消息记录、清空后不再返回、不存在的会话 404 |

## 设计说明

1. **为什么会话存储单独成 `app/store.py`**：作业要求「读写集中在一个模块，方便以后换成数据库」，
   路由层只调用 `append / get / list_ids / delete`，替换实现时不用改接口。
2. **为什么用 `create_app()` 工厂 + 依赖注入**：测试里传入假的 `Settings`、`SessionStore`、
   假客户端即可，完全不碰网络和真实 `.env`。
3. **为什么先调模型再写历史**：调用失败时不会在会话里留下「有提问没回答」的半截记录。
4. **为什么同步路由**：模型 SDK 是同步的，FastAPI 会把 `def` 路由放进线程池，不阻塞事件循环；
   线程安全由 `SessionStore` 内部的 `RLock` 保证。

## 开发流程

仓库采用功能分支 + PR 的方式迭代，`main` 分支受保护：

- `feat/fastapi-chat-sessions`：FastAPI 骨架、对话接口、会话管理
- `main`：只通过 PR 合并

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat: 新增 FastAPI 对话接口
test: 新增会话管理离线测试
docs: 补充接口调用说明
```
