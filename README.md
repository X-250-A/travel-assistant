# 旅游助手 Agent (Trip Agent)

基于 DeepSeek V4 大模型的智能旅游规划助手，通过多轮对话理解用户偏好，自动生成结构化行程方案。

## 功能概览

- **用户认证** — JWT 注册/登录，bcrypt 密码哈希
- **AI 多轮对话** — SSE 流式输出，Agent 编排工具调用，自动识别规划意图
- **行程生成** — LLM 根据对话内容生成包含每日安排、景点推荐、出行贴士的结构化行程 JSON
- **历史行程管理** — 行程列表浏览、详情查看、删除

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.14 + FastAPI + SQLAlchemy 2.0 (async) |
| 前端 | Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS 4 |
| 数据库 | MySQL 8.0 (aiomysql) |
| AI | DeepSeek API (兼容 OpenAI SDK 调用) |

## 项目结构

```
├── backend/
│   └── app/
│       ├── main.py              # FastAPI 应用入口，CORS，路由注册
│       ├── config.py            # pydantic-settings 环境变量配置
│       ├── db/session.py        # SQLAlchemy async engine & session
│       ├── models/              # ORM: User, Trip, Message
│       ├── schemas/             # Pydantic 请求/响应模型
│       ├── routers/             # auth(注册登录), chat(SSE流式), trips(CRUD)
│       ├── crud/                # 数据库操作: user, trip, message
│       ├── services/            # LLM 客户端 + Prompt 构建器
│       ├── agent/               # 会话管理 + 行程规划 Agent
│       └── utils/               # JWT, 密码哈希
├── frontend/
│   ├── app/                     # Next.js App Router 页面
│   │   ├── page.tsx             # 首页（行程列表）
│   │   ├── login/page.tsx       # 登录页
│   │   ├── register/page.tsx    # 注册页
│   │   └── trips/[id]/page.tsx  # 行程详情页
│   ├── components/              # UI 组件 & 业务组件
│   │   ├── ui/                  # Button, Card, Loading
│   │   ├── trip/                # TripCard, TripDetail
│   │   └── chat/                # ChatContainer, ChatInput, MessageBubble, StreamingText
│   ├── hooks/                   # useAuth, useChat
│   ├── lib/api.ts               # HTTP 客户端 + SSE 流式请求
│   └── types/index.ts           # TypeScript 类型定义
└── .env.example
```

## 快速开始

### 1. 环境准备

- Python 3.14+
- Node.js 20+
- MySQL 8.0（本地运行）

### 2. 后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（从项目根目录拷贝）
cp ../.env.example ../.env
# 编辑 .env，填入 DeepSeek API Key 和本地 MySQL 连接信息

# 启动
uvicorn backend.app.main:app --reload --port 8000
```

### 3. 前端

```bash
cd frontend

npm install
npm run dev
```

浏览器打开 `http://localhost:3000`，注册账号后即可使用。

## 环境变量

| 变量 | 说明 | 示例 |
|---|---|---|
| `DATABASE_URL` | 数据库连接串 | `mysql+aiomysql://root:password@localhost:3306/trip-agent` |
| `SECRET_KEY` | JWT 签名密钥 | 随机字符串 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-xxx` |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名 | `deepseek-v4-flash` |
| `MAX_CONTEXT_TOKENS` | 上下文窗口上限 | `6000` |
| `CORS_ORIGINS` | 允许的前端域名 | `http://localhost:3000` |

## API 接口

### 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录（返回 JWT） |

### 对话

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 发送消息（SSE 流式响应） |

### 行程

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/trips` | 行程列表 |
| GET | `/api/trips/{id}` | 行程详情 |
| PATCH | `/api/trips/{id}` | 更新行程 |
| DELETE | `/api/trips/{id}` | 删除行程 |
| GET | `/api/trips/{id}/messages` | 行程对话历史 |

所有接口（除注册/登录外）需携带 `Authorization: Bearer <token>` 请求头。

## 文档

- [架构设计](旅游助手Agent架构设计.md)
- [API 接口规范](旅游助手AgentAPI接口规范.md)
