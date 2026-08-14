# 旅游助手 Agent (Trip Agent)

基于 DeepSeek V4 大模型的智能旅游规划助手，通过多轮对话理解用户偏好，自动生成结构化行程方案。

> **最新版本**: [v0.8.0](https://github.com/X-250-A/travel-assistant/releases/tag/v0.8.0) — "Critic 复盘" 🧐 | [更新日志](RELEASE_NOTES.md)

## 功能概览

- **用户认证** — JWT 注册/登录，bcrypt 密码哈希
- **AI 多轮对话** — SSE 流式输出，Agent 编排工具调用，LLM 意图分类 + 闲聊分流
- **行程生成** — LLM 根据对话内容生成包含每日安排、景点推荐、出行贴士的结构化行程 JSON，支持确认/草稿状态
- **天气预报** — 通过工具调用自动查询目的地天气，融入行程建议
- **预算估算** — 根据天数/人数/档次（经济/舒适/豪华）自动计算旅行预算
- **历史行程管理** — 行程列表、详情查看、删除

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.14 + FastAPI + SQLAlchemy 2.0 (async) |
| 前端 | Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS 4 |
| 数据库 | SQLite (aiosqlite)，可选切换 MySQL 8.0 (aiomysql) |
| AI | DeepSeek API (兼容 OpenAI SDK 调用)，支持 Function Calling |
| 容器化 | Docker + docker-compose (backend + frontend + mysql) |

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
│       ├── agent/               # 会话管理 + 行程规划 Agent + 意图分类
│       ├── tools/               # 工具注册中心 + 天气 + 预算计算
│       │   ├── base.py          # Tool dataclass 统一工具定义
│       │   ├── __init__.py      # 工具注册与调度
│       │   ├── weather.py       # 天气预报工具
│       │   └── budget_calculate.py  # 预算估算工具
│       ├── middleware/           # 认证中间件
│       └── utils/               # JWT, 密码哈希
├── frontend/
│   ├── app/                     # Next.js App Router 页面
│   │   ├── page.tsx             # 首页（聊天 + 行程规划）
│   │   ├── login/page.tsx       # 登录页
│   │   ├── register/page.tsx    # 注册页
│   │   ├── trips/page.tsx       # 行程列表页
│   │   └── trips/[id]/page.tsx  # 行程详情页
│   ├── components/              # UI 组件 & 业务组件
│   │   ├── ui/                  # Button, Card, Loading
│   │   ├── trip/                # TripCard, TripDetail
│   │   ├── chat/                # ChatContainer, ChatInput, MessageBubble, StreamingText
│   │   └── auth/                # AuthForm
│   ├── hooks/                   # useAuth, useChat
│   ├── lib/api.ts               # HTTP 客户端 + SSE 流式请求
│   └── types/index.ts           # TypeScript 类型定义
├── docker-compose.yml
├── .env.example
└── RELEASE_NOTES.md
```

## 快速开始

### 1. 环境准备

- Python 3.14+
- Node.js 20+
- 零配置即可运行（默认 SQLite，无需安装数据库）

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
# 开发默认使用 SQLite，无需改数据库。填入 DeepSeek API Key 即可

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

### 4. Docker 部署

```bash
# 启动全部服务（backend + frontend + mysql）
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 环境变量

| 变量 | 说明 | 示例 |
|---|---|---|
| `DATABASE_URL` | 数据库连接串 | `sqlite+aiosqlite:///./trip_agent.db` |
| `SECRET_KEY` | JWT 签名密钥 | 随机字符串 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-xxx` |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名 | `deepseek-v4-flash` |
| `MAX_CONTEXT_TOKENS` | 上下文窗口上限 | `6000` |
| `WEATHER_API_KEY` | （可选）OpenWeatherMap API Key | 用于天气预报工具 |
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
| POST | `/api/chat` | 发送消息（SSE 流式响应，支持 Function Calling） |

### 行程

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/trips` | 行程列表 |
| GET | `/api/trips/{id}` | 行程详情 |
| PATCH | `/api/trips/{id}` | 更新行程 |
| DELETE | `/api/trips/{id}` | 删除行程 |
| GET | `/api/trips/{id}/messages` | 行程对话历史 |

所有接口（除注册/登录外）需携带 `Authorization: Bearer <token>` 请求头。

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| [v0.8.0](https://github.com/X-250-A/travel-assistant/releases/tag/v0.8.0) | 2026-08-09 | 行程方案 Critic 复盘（自评自纠）—— 二轮审查 + 条件重生成 |
| [v0.7.0](https://github.com/X-250-A/travel-assistant/releases/tag/v0.7.0) | 2026-08-07 | ReAct 推理循环（Thought-Action-Observation）+ 反思机制 |
| [v0.6.0](https://github.com/X-250-A/travel-assistant/releases/tag/v0.6.0) | 2026-08-04 | Agent 记忆系统（偏好提取 + 跨会话持久化）+ 行程确认/编辑接后端 |
| [v0.5.0](https://github.com/X-250-A/travel-assistant/releases/tag/v0.5.0) | 2026-08-02 | Redis 集成：Token 黑名单 + 滑动窗口限流 + 天气缓存 |
| [v0.4.0](https://github.com/X-250-A/travel-assistant/releases/tag/v0.4.0) | 2026-07-29 | 前端 UI 全面优化 + 后端工具注册机制重构 + 预算计算工具 |
| v0.3.0 | 2026-07-27 | LLM 意图分类 + 闲聊分流 + 工具调用循环防护 |
| v0.2.0 | 2026-07-25 | Tool Calling 机制 + 天气预报工具 |
| v0.1.0 | 2026-07-24 | MVP 发布 |

详见 [RELEASE_NOTES.md](RELEASE_NOTES.md)

## 文档

- [架构设计](旅游助手Agent架构设计.md)
- [API 接口规范](旅游助手AgentAPI接口规范.md)
