# 聊天机器人（backend + frontend）

仓库从本次作业起改成了清晰的前后端两目录结构：

```
chatbot/
├── backend/     # 聊天机器人后端：FastAPI + SQLAlchemy ORM + SQLite + 自带网页聊天界面
└── frontend/    # Vue 3 + Vite 空工程（脚手架，尚未接入 API）
```

## backend/：后端

技术栈：Python 3.10+、FastAPI、SQLAlchemy 2.x、SQLite。

```bash
cd backend
pip install -r requirements.txt
copy .env.example .env        # Windows；Linux/macOS 用 cp
# 编辑 .env，至少填写 CHATBOT_API_KEY
python -m app                 # 启动服务：http://127.0.0.1:8000
```

> 所有后端命令都必须在 `backend/` 目录下执行：`chat.db`、`static/` 都相对这个目录解析。

- 接口文档：<http://127.0.0.1:8000/docs>
- 自带的网页聊天界面：<http://127.0.0.1:8000>
- 测试：

  ```bash
  cd backend
  pytest -v
  # 41 passed（离线，mock 模型客户端，不需要真实 Key）
  ```

- 数据库：`backend/chat.db`（SQLite，启动时自动建表），已被 `.gitignore` 忽略，
  旧的聊天记录可以继续读取。
- 更详细的功能、接口、ORM 与 ER 图说明见 [`backend/README.md`](backend/README.md)。

## frontend/：前端

技术栈：Vue 3 + Vite（JavaScript）。

```bash
cd frontend
npm install
npm run dev                   # 浏览器打开 http://localhost:5173
```

其他命令：

```bash
npm run build                 # 生产构建
npm run preview               # 预览构建产物
```

> 本次前端只是 `npm create vue` 生成的脚手架，**尚未接入后端 API**，
> 打开后是 Vue 的默认欢迎页；组件、路由、接口调用留到下一阶段。

## 仓库卫生

根目录 `.gitignore` 与 `frontend/.gitignore` 已忽略：`node_modules/`、`dist/`、
`.env`、`*.db`、`__pycache__/` 等；仓库里不会提交依赖目录、构建产物、密钥或数据库文件。

## 开发流程

`main` 分支受保护，改动都走功能分支 + PR，提交信息遵循
[Conventional Commits](https://www.conventionalcommits.org/)。
