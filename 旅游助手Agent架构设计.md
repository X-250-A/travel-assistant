# 旅游助手 Agent 架构设计

> 本项目类型为 Web 应用（前后端分离），处于从零构思阶段。

---

## 1. 项目概述

旅游助手 Agent 是一个面向国内游的行程规划智能体，以对话式交互为核心：用户在聊天界面描述旅行意图，Agent 理解需求后调用 DeepSeek 生成结构化行程，用户可继续通过对话调整，Agent 根据上下文持续优化方案。

**Agent 的三个特征**：

1. **对话式交互**：多轮对话、逐步细化需求
2. **上下文管理**：记住用户偏好、已讨论的行程、修改历史
3. **工具编排（v2.0 预留）**：Agent 自主决定何时搜索景点、查询天气、比对交通方案

**MVP 范围（v1.0）**：对话式创建行程 → DeepSeek 生成行程 → 用户反馈调整 → 保存/查看历史。用户注册/登录纳入。

**架构原则**：后端 FastAPI + 前端 Next.js 15，REST API 通信。FastAPI 承担 Agent 编排逻辑，Next.js 承担聊天 UI 和渲染。

---

## 2. 系统架构

```mermaid
graph TB
    subgraph "Next.js 15 前端"
        A["Chat UI<br/>对话界面"]
        B["行程展示卡片<br/>结构化行程渲染"]
        C["用户认证页面<br/>登录/注册"]
    end

    subgraph "FastAPI 后端"
        subgraph "路由层"
            D["chat API<br/>POST /api/chat"]
            E["trip API<br/>GET/POST /api/trips"]
            F["auth API<br/>POST /api/auth/*"]
        end
        subgraph "Agent 编排层"
            G["ConversationManager<br/>会话状态机、上下文管理"]
            H["TripPlannerAgent<br/>行程规划 Agent 核心"]
        end
        subgraph "服务层"
            I["LLMClient<br/>DeepSeek SDK 封装"]
            J["PromptBuilder<br/>System Prompt + 上下文组装"]
        end
        subgraph "数据层"
            K["SQLAlchemy ORM<br/>User / Trip / Message"]
        end
    end

    subgraph "外部服务"
        L["DeepSeek API<br/>Chat Completion"]
    end

    subgraph "数据存储"
        M[("SQLite 开发<br/>MySQL 生产")]
    end

    A -->|"SSE / JSON"| D
    B -->|"JSON"| E
    C -->|"JSON"| F
    D --> G
    G --> H
    H --> J
    H --> I
    I -->|"OpenAI 兼容"| L
    G --> K
    H --> K
    K --> M
```

**分层说明**：

| 层 | 职责 | 为什么放在这里 |
|----|------|---------------|
| Next.js 前端 | 聊天 UI、行程卡片渲染、用户认证页面 | 前后端分离，AI 对 Next.js/React 生态的代码生成质量最高 |
| 路由层 | HTTP 请求接入、参数校验、响应序列化 | FastAPI 的优势层——Pydantic 校验 + 自动文档 |
| Agent 编排层 | 多轮对话状态管理、Agent 决策逻辑、上下文窗口控制 | 项目的核心——"Agent 的大脑"，独立一层便于测试和演进 |
| 服务层 | DeepSeek API 调用封装、Prompt 模板管理 | 与编排层解耦——切换模型或调整 Prompt 只需改这一层 |
| 数据层 | ORM 实体定义、数据库操作 | 标准持久化层，SQLAlchemy 统一 SQLite 和 MySQL |

**通信方式**：
- 前端 ↔ 后端：REST JSON API + SSE（Server-Sent Events，流式输出）
- 后端 ↔ DeepSeek：HTTP（OpenAI 兼容 SDK）
- 后端 ↔ 数据库：SQLAlchemy Session

---

## 3. 技术选型说明

| 技术 | 用途 | 选型理由 |
|------|------|---------|
| Python 3.14 | 后端语言 | 已掌握；LLM 生态最成熟 |
| FastAPI | 后端 Web 框架 | 原生 async/await、Pydantic 类型校验、自动 OpenAPI 文档 |
| Next.js 15 (App Router) | 前端框架 | 业界主流 React 元框架；AI 代码生成对此生态支持极好 |
| TypeScript | 前端语言 | 类型安全，AI 生成的 Next.js 代码默认用 TS |
| DeepSeek Chat API | LLM 推理 | 已有 API Key；中文能力强；兼容 OpenAI 接口格式 |
| openai (Python SDK) | LLM 调用 | DeepSeek 兼容 OpenAI 接口 |
| SQLAlchemy 2.0 | ORM | 兼容 SQLite 和 MySQL；2.0 原生支持 async |
| SQLite → MySQL 8.0 | 数据库 | 开发零配置，生产已有经验 |
| Docker + Compose | 部署 | 已掌握，一键启动全栈 |

### 未选型决策

- CSS 方案：Tailwind CSS v4？shadcn/ui？建议先 Tailwind，需要组件时引入 shadcn/ui
- 前端状态管理：React Context + useReducer？Zustand？v1.0 建议 Context
- 流式输出方案：SSE？WebSocket？v1.0 建议 SSE

---

## 4. 后端核心概念简介

**JWT (JSON Web Token) — 用户认证**

bcrypt 加密密码存入数据库只是注册环节。用户登录后，后端颁发一个"通行证"（JWT），之后每次请求前端都带上这个通行证。流程：用户登录 → 验证密码 → 生成 JWT（user_id + 过期时间）→ 前端存浏览器 → 后续请求 Header 携带 `Authorization: Bearer <JWT>` → 后端中间件解码验证。JWT 是无状态令牌——后端不需要记住谁登录了，签名有效就信任。

**中间件 (Middleware)**

中间件是每个请求必经的"关卡"。认证中间件检查请求是否带有效 JWT，没带就返回 401。不用在每个路由函数里写认证逻辑。

**数据库关系 (Relationship)**

用户和行程之间是一对多关系（一个用户可有多个行程）。SQLAlchemy 通过 `relationship()` 定义，查询时用 `user.trips` 直接拿到该用户的所有行程。

**依赖注入 (Dependency Injection)**

FastAPI 用 `Depends()` 实现。`def get_db()` 返回数据库会话，路由函数写 `db: Session = Depends(get_db)` 就能自动获得数据库连接。测试时可替换 `get_db` 返回内存数据库。

**SSE (Server-Sent Events)**

Agent 生成行程可能需十几秒，用户不能干等。SSE 让服务端流式推送内容到前端：DeepSeek 每生成一段文字，就推送一段到前端显示（ChatGPT 逐字输出效果）。

---

## 5. 目录结构详解

### 5.1 项目根目录

```
trip-agent/
├── backend/                    # FastAPI 后端服务
├── frontend/                   # Next.js 15 前端应用
├── docker-compose.yml          # 一键启动全栈
├── .env.example                # 环境变量模板
├── .gitignore
└── README.md
```

### 5.2 后端目录 (`backend/`)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用工厂，注册路由、中间件、生命周期事件
│   ├── config.py               # 配置管理：从 .env 读取所有配置项到 Pydantic Settings
│   │
│   ├── utils/                   # 工具层 —— 通用函数和工具
│   │   ├── __init__.py
│   │   ├── security.py          # bcrypt 密码哈希与校验
│   │   └── jwt.py               # JWT Token 创建与验证
│   │
│   ├── routers/                # 路由层 —— 只做请求解析和响应格式化
│   │   ├── __init__.py
│   │   ├── auth.py             # POST /api/auth/register, /api/auth/login
│   │   ├── chat.py             # POST /api/chat  (SSE 流式响应)
│   │   └── trips.py            # GET /api/trips, GET /api/trips/{id}, DELETE /api/trips/{id}
│   │
│   ├── agent/                  # Agent 编排层 —— 整个后端的核心
│   │   ├── __init__.py
│   │   ├── conversation.py     # ConversationManager：会话状态机、历史消息管理
│   │   └── planner.py          # TripPlannerAgent：行程规划的核心 Agent 逻辑
│   │
│   ├── services/               # 服务层 —— 可替换的底层能力
│   │   ├── __init__.py
│   │   ├── llm_client.py       # DeepSeek API 封装（重试、超时、流式）
│   │   └── prompt_builder.py   # System Prompt 模板 + 上下文拼接
│   │
│   │
│   ├── crud/                   # CRUD 层 —— 数据库增删改查函数，与路由层解耦
│   │   ├── __init__.py
│   │   ├── user.py             # User 的 CRUD
│   │   ├── trip.py             # Trip 的 CRUD
│   │   └── message.py          # Message 的 CRUD
│   │
│   ├── models/                 # 数据层 —— SQLAlchemy ORM 实体
│   │   ├── __init__.py
│   │   ├── base.py             # declarative_base + 通用 mixin（id, created_at, updated_at）
│   │   ├── user.py             # User 实体
│   │   ├── trip.py             # Trip 实体（关联 User）
│   │   └── message.py          # Message 实体（关联 Trip，存放对话历史）
│   │
│   ├── schemas/                # Pydantic 请求/响应模型（与 ORM 模型分离）
│   │   ├── __init__.py
│   │   ├── auth.py             # RegisterRequest, LoginRequest, TokenResponse
│   │   ├── chat.py             # ChatRequest, ChatStreamChunk
│   │   └── trip.py             # TripResponse, TripCreate
│   │
│   ├── middleware/              # FastAPI 中间件
│   │   ├── __init__.py
│   │   └── auth_middleware.py  # JWT 验证中间件，提取 current_user 注入请求上下文
│   │
│   └── db/
│       ├── __init__.py
│       └── session.py          # SQLAlchemy async engine + session factory + get_db 依赖
│
├── tests/                      # 后端测试
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_chat.py
│   └── test_planner.py
│
├── alembic/                    # 数据库迁移（v1.0 可选，先用 SQLAlchemy create_all）
├── alembic.ini
├── requirements.txt
├── Dockerfile
└── .env                        # 实际配置（gitignore）
```

**为什么路由和 Agent 分离**：Agent 逻辑（conversation.py + planner.py）独立于 HTTP——理论上可抽出来换 CLI 入口或 WebSocket 入口，核心逻辑不动。路由层只是薄薄的适配层。

### 5.3 前端目录 (`frontend/`)

```
frontend/
├── app/                        # Next.js App Router 约定目录
│   ├── layout.tsx              # 根布局（html, body, 全局 Provider）
│   ├── page.tsx                # 首页（未登录 → 引导页，已登录 → 聊天页）
│   ├── login/page.tsx          # 登录页
│   ├── register/page.tsx       # 注册页
│   ├── trips/page.tsx          # 历史行程列表
│   ├── trips/[id]/page.tsx     # 单个行程详情
│   └── globals.css             # Tailwind + 全局样式
│
├── components/                 # React 组件
│   ├── chat/
│   │   ├── ChatContainer.tsx   # 聊天主容器（消息列表 + 输入框）
│   │   ├── MessageBubble.tsx   # 单条消息气泡（区分用户/Agent）
│   │   ├── ChatInput.tsx       # 输入框
│   │   └── StreamingText.tsx   # SSE 流式文本逐字渲染组件
│   ├── trip/
│   │   ├── TripCard.tsx        # 行程摘要卡片
│   │   └── TripDetail.tsx      # 行程详情（每日景点、交通、用餐）
│   ├── auth/
│   │   └── AuthForm.tsx        # 登录/注册表单（复用组件）
│   └── ui/                     # 通用 UI 组件
│       ├── Button.tsx
│       ├── Card.tsx
│       └── Loading.tsx
│
├── lib/
│   └── api.ts                  # FastAPI 请求封装（fetch + JWT 注入）
│
├── hooks/                      # 自定义 React Hooks
│   ├── useChat.ts              # 聊天核心 hook：发消息、接收 SSE 流、消息列表状态
│   └── useAuth.ts              # 认证 hook：登录/注册/登出/获取当前用户
│
├── types/
│   └── index.ts                # User, Trip, Message, ChatResponse 等类型
│
├── public/
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── Dockerfile
└── .env.local                  # 前端环境变量（后端 API 地址）
```

部署通信：前端在浏览器端通过 `fetch()` 直连后端 API（CORS 白名单），Docker Compose 将二者放在同一网络内。

---

## 6. 模块设计

### 6.1 认证模块 (`routers/auth.py` + `middleware/auth_middleware.py`)

**模块职责**：处理用户注册、登录，为受保护接口提供 JWT 身份验证。

**对外接口**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/register` | POST | 注册新用户，接收 username + password，返回 UserResponse |
| `/api/auth/login` | POST | 验证凭据，返回 `{ access_token, token_type }` |
| `get_current_user` | FastAPI Depends | 中间件函数，解析 JWT 返回 User 对象 |

**依赖关系**：依赖 `models/user.py`、`schemas/auth.py`；被 `routers/chat.py`、`routers/trips.py` 依赖（通过 `get_current_user`）。

**关键实现细节**：密码用 `passlib[bcrypt]` 哈希存储；JWT 使用 `python-jose`，签名密钥从 `config.py` 的 `SECRET_KEY` 读取，默认 7 天过期；`get_current_user` 用 `Depends` 注入保护路由。

### 6.2 Agent 编排层

#### 6.2.1 ConversationManager (`agent/conversation.py`)

**模块职责**：管理一次行程规划对话的完整生命周期——创建会话、追踪状态、维护消息历史、控制上下文窗口大小。

**对外接口**：

| 方法 | 说明 |
|------|------|
| `create_conversation(trip_id, user_id)` | 创建新会话，关联到某个 Trip |
| `add_message(role, content)` | 追加一条消息到会话历史 |
| `get_context(max_tokens)` | 返回拼接后的上下文字符串，自动裁剪到 max_tokens 以内 |
| `get_state()` | 返回当前会话状态（idle / planning / confirming / done） |

**关键实现细节**：会话状态机用简单的 if-elif 实现，四个状态按顺序流转；上下文窗口管理从消息历史尾部向前截取，保证不截断单轮对话；每条消息即时写入数据库，避免内存 OOM。

#### 6.2.2 TripPlannerAgent (`agent/planner.py`)

**模块职责**：封装行程规划 Agent 的核心决策逻辑——理解用户意图、构建 Prompt、调用 LLM、解析行程结果、处理用户反馈。

**对外接口**：

| 方法 | 说明 |
|------|------|
| `handle_message(user_input, conversation)` | Agent 主入口：接收用户消息，返回 Agent 回复（流式） |
| `_classify_intent(user_input)` | 分类用户意图：new_trip / modify_trip / ask_question / unclear |
| `_generate_plan(conversation)` | 构造 Prompt 调用 LLM 生成行程 |
| `_apply_feedback(feedback, current_plan, conversation)` | 根据用户反馈调整现有行程 |

**关键实现细节**：意图分类用关键词匹配 + 上下文判断（v1.0 规则，省一次 LLM 调用）；行程生成采用"单次生成 + 迭代修正"策略；结构化输出通过 System Prompt 要求 JSON + `response_format: json_object` 保证；流式输出返回 `AsyncGenerator[str]`，边生成边 yield。

### 6.3 服务层

#### 6.3.1 LLMClient (`services/llm_client.py`)

**模块职责**：封装 DeepSeek API 调用细节，对上层提供统一的流式/非流式调用接口。

**对外接口**：

| 方法 | 说明 |
|------|------|
| `chat(messages, stream=False)` | 非流式调用，返回完整响应文本 |
| `chat_stream(messages)` | 流式调用，返回 `AsyncGenerator[str]` |
| `count_tokens(text)` | 估算 Token 数 |

**关键实现细节**：网络错误重试 3 次，指数退避（1s/2s/4s）；首次请求 60s 超时；Token 计数优先用 tiktoken，fallback 用 `len(text) // 2`。

#### 6.3.2 PromptBuilder (`services/prompt_builder.py`)

**模块职责**：管理 Prompt 模板，根据会话上下文动态拼接 messages 数组。

**对外接口**：

| 方法 | 说明 |
|------|------|
| `build_system_prompt()` | 返回 System Prompt（静态模板） |
| `build_messages(conversation_context, user_input)` | 拼接 messages 数组 |

**关键实现细节**：System Prompt 存放在 `services/prompts/` 目录下为独立 `.txt` 文件；拼接时自动检查 Token 数，超出限制时裁剪最早的消息（保留 System Prompt 始终在首位）。

### 6.4 数据层 (`models/`)

三个核心实体及其关系：

```mermaid
erDiagram
    User ||--o{ Trip : "创建"
    Trip ||--o{ Message : "包含"

    User {
        uuid id PK
        string username "唯一"
        string hashed_password "bcrypt"
        datetime created_at
    }

    Trip {
        uuid id PK
        uuid user_id FK
        string title "如'成都三日美食之旅'"
        json plan_data "LLM 生成的完整行程 JSON"
        string status "draft / confirmed"
        datetime created_at
        datetime updated_at
    }

    Message {
        uuid id PK
        uuid trip_id FK
        string role "user / assistant / system"
        text content
        datetime created_at
    }
```

**关键设计考量**：`plan_data` 用 JSON 字段——行程结构复杂，JSON 比拆多张关系表更灵活，LLM 输出直接存，字段变化只改 Prompt 不改 schema；密码不存明文，bcrypt 哈希存储。

### 6.5 前端简化方案

前端直连后端：`lib/api.ts` 封装 `fetch()`，每次请求在 Header 附带 JWT；后端 FastAPI 配置 CORS；JWT 存在 `localStorage`。不做 BFF 层，不做 Nginx 反代。

---

## 7. 开发分阶段路线

### 阶段 0：环境搭建 + 跑通骨架（预计 1-2 天）

**目标**：前后端都能启动，能通信。

做这些事：
1. `backend/` 下创建 FastAPI 空应用，`/api/health` 端点
2. `frontend/` 下 `npx create-next-app@latest`
3. 前端按钮点击 fetch `localhost:8000/api/health`，显示结果

**学什么**：FastAPI 基本路由、Next.js 项目结构、CORS 配置

### 阶段 1：用户注册/登录（预计 2-3 天）

**目标**：能注册账号、登录拿到 JWT、用 JWT 访问受保护接口。

做这些事：
1. `models/user.py`：User 实体 + bcrypt
2. `routers/auth.py`：register + login
3. `middleware/auth_middleware.py`：JWT 验证
4. `/api/me` 端点验证认证链路
5. 前端注册页、登录页

**学什么**：JWT 认证全流程、bcrypt、SQLAlchemy CRUD、FastAPI Depends 注入、localStorage

### 阶段 2：调用 DeepSeek 生成行程（预计 2-3 天）

**目标**：后端能向 DeepSeek 发请求，拿到行程 JSON 并解析。

做这些事：
1. `services/llm_client.py`：封装 DeepSeek 调用（非流式）
2. `services/prompt_builder.py`：System Prompt 模板
3. `/api/test-plan` 测试端点
4. 测试输入"北京三日游"，验证返回的 JSON

**学什么**：LLM API 调用、Prompt Engineering 基础、JSON 解析与错误处理

**注意**：此阶段不涉及 Agent、多轮对话、流式输出。

### 阶段 3：对话式 Agent（预计 3-4 天）

**目标**：把阶段 2 的单次调用升级为多轮对话 Agent。

做这些事：
1. `models/trip.py` + `models/message.py`
2. `agent/conversation.py`：ConversationManager
3. `agent/planner.py`：TripPlannerAgent
4. `routers/chat.py`：POST /api/chat（SSE 流式）
5. 前端聊天 UI

**学什么**：Agent 感知-决策-执行循环、多轮对话上下文管理、SSE 流式输出、React 聊天 UI

### 阶段 4：行程管理（预计 1-2 天）

**目标**：能查看、删除历史行程。

做这些事：
1. `routers/trips.py`：GET 列表、详情、DELETE
2. 前端 `/trips` 页面

**学什么**：RESTful API 设计、Next.js 动态路由

### 阶段 5：打磨 + 部署（预计 1-2 天）

**目标**：项目能跑在 Docker 里。

做这些事：
1. 前端 UI 打磨（Tailwind）
2. `docker-compose.yml`：backend + frontend + MySQL
3. `.env` 配置整理

**学什么**：Docker Compose 多服务编排

> 总时间估算：约 9-14 天（每天 3-4 小时）。

---

## 8. 核心流程

### 8.1 创建新行程（首次对话）

```mermaid
sequenceDiagram
    actor U as 用户
    participant FE as Next.js 前端
    participant R as FastAPI<br/>routers/chat.py
    participant CM as ConversationManager
    participant TPA as TripPlannerAgent
    participant PB as PromptBuilder
    participant LLM as LLMClient
    participant DB as 数据库
    participant DS as DeepSeek API

    U->>FE: 输入"我想去成都玩三天，预算3000，喜欢美食"
    FE->>R: POST /api/chat { message: "..." }
    R->>R: JWT 中间件验证身份
    R->>CM: create_conversation(trip_id, user_id)
    CM->>DB: INSERT Trip(status=draft) + INSERT Message(role=user)
    CM-->>R: conversation 对象

    R->>TPA: handle_message(user_input, conversation)
    TPA->>TPA: _classify_intent() → "new_trip"
    TPA->>CM: get_context(max_tokens=6000)
    CM-->>TPA: 拼接后的消息历史
    TPA->>PB: build_messages(context, user_input)
    PB-->>TPA: [{role: "system", ...}, {role: "user", ...}]

    TPA->>LLM: chat_stream(messages)
    LLM->>DS: POST /v1/chat/completions (stream=true)
    DS-->>LLM: data: {"delta": "第一天..."}
    LLM-->>TPA: AsyncGenerator[chunk]

    loop 流式推送
        TPA-->>R: yield chunk
        R-->>FE: SSE data: chunk
        FE->>FE: StreamingText 逐字渲染
    end

    TPA->>DB: UPDATE Trip(plan_data=json, title="成都三日美食之旅")
    TPA->>CM: add_message(role="assistant", content=完整回复)
    CM->>DB: INSERT Message(role=assistant)
    TPA-->>R: [流结束]
    R-->>FE: SSE event: done
    FE->>FE: 渲染行程卡片
```

流程要点：意图分类→上下文组装→LLM 流式生成→即时写库。流式推送让用户看到逐字输出而非干等。即时写库保证刷新页面不丢数据。

### 8.2 用户反馈调整行程

```mermaid
sequenceDiagram
    actor U as 用户
    participant FE as Next.js 前端
    participant R as FastAPI<br/>routers/chat.py
    participant CM as ConversationManager
    participant TPA as TripPlannerAgent
    participant DB as 数据库

    U->>FE: "第二天太赶了，去掉杜甫草堂"
    FE->>R: POST /api/chat { message: "...", trip_id: "xxx" }
    R->>R: JWT 中间件验证 + 校验 trip 属于当前用户
    R->>CM: 加载已有 conversation (通过 trip_id)
    CM->>DB: SELECT messages WHERE trip_id=xxx ORDER BY created_at
    CM-->>R: conversation (含历史消息 + 已有 plan_data)

    R->>TPA: handle_message(user_input, conversation)
    TPA->>TPA: _classify_intent() → "modify_trip"
    TPA->>DB: SELECT plan_data FROM trips WHERE id=xxx
    DB-->>TPA: 当前完整行程 JSON
    TPA->>TPA: _apply_feedback("去掉杜甫草堂", current_plan)

    Note over TPA: 将反馈 + 当前行程 JSON + 历史对话<br/>拼接为 Prompt，要求 LLM 局部调整

    TPA->>LLM: chat_stream(modified_messages)
    LLM-->>TPA: 流式返回调整后的行程

    loop 流式推送
        TPA-->>R: yield chunk
        R-->>FE: SSE data: chunk
    end

    TPA->>DB: UPDATE Trip(plan_data=新json, updated_at=now)
    TPA->>CM: add_message(role="assistant", content=...)
    TPA-->>R: [流结束]
    R-->>FE: SSE event: done
    FE->>FE: 更新行程卡片（原地替换旧内容）
```

流程要点：把"当前行程 JSON + 用户反馈 + 历史对话"三合一作为 Prompt 输入，指令 LLM 局部修改而非全新生成。

---

## 9. 数据模型深入

### 9.1 plan_data JSON 结构

```json
{
  "destination": "成都",
  "duration": 3,
  "budget": 3000,
  "style": ["美食", "人文"],
  "overview": "三日行程涵盖成都市区经典景点...",

  "days": [
    {
      "day": 1,
      "date": null,
      "theme": "市区人文初探",
      "attractions": [
        {
          "name": "宽窄巷子",
          "type": "景点",
          "duration_minutes": 120,
          "cost_yuan": 0,
          "tips": "建议上午去，人少适合拍照",
          "transport_from_previous": null
        }
      ],
      "meals": [
        {
          "meal_type": "lunch",
          "suggestion": "奎星楼街吃串串，人均 40-60 元",
          "location_near": "宽窄巷子周边"
        }
      ]
    }
  ],

  "overall_tips": "6月成都多雨，建议带伞；地铁覆盖主要景点，无需租车"
}
```

**字段考量**：`transport_from_previous` 让行程有"路径感"；`theme` 每日主题标签，让行程有叙事节奏；`cost_yuan` 门票费用，v2.0 与 budget 对比做预算摘要。

### 9.2 为什么不用多张关系表

| 方案 | 优点 | 缺点 |
|------|------|------|
| JSON 字段（本项目采用） | LLM 产出直接存，零转换；前端直接渲染；加字段不改数据库 | 不能 SQL 查询"包含宽窄巷子的所有行程" |
| 拆多张关系表 | 支持复杂 SQL 查询和分析 | 需要把 LLM 的 JSON 拆解为多条 INSERT；字段变更要改表结构 + 代码 |

当前项目是行程生成工具，不是数据分析平台——JSON 字段是合适的选择。

---

## 10. 配置与部署

### 10.1 环境变量清单

**后端 (`backend/.env`)**：

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接串 | `sqlite+aiosqlite:///./trip_agent.db` (开发) / `mysql+asyncmy://user:pass@mysql:3306/trip_agent` (生产) |
| `SECRET_KEY` | JWT 签名密钥 | `openssl rand -hex 32` 生成 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-xxx` |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名 | `deepseek-v4-flash` |
| `MAX_CONTEXT_TOKENS` | 上下文窗口上限 | `6000` |
| `CORS_ORIGINS` | 允许的前端域名 | `http://localhost:3000` |

**前端 (`frontend/.env.local`)**：

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `NEXT_PUBLIC_API_URL` | 后端地址 | `http://localhost:8000` |

### 10.2 部署拓扑

```mermaid
graph LR
    subgraph "Docker Compose"
        A["Next.js 前端<br/>port 3000"]
        B["FastAPI 后端<br/>port 8000"]
        C[("MySQL 8.0<br/>port 3306")]
    end

    D["用户浏览器"] -->|":3000"| A
    A -->|":8000"| B
    B -->|":3306"| C
```

`docker-compose.yml` 结构：

```yaml
services:
  backend:
    build: ./backend
    ports: [ "8000:8000" ]
    env_file: .env
    depends_on: [ mysql ]

  frontend:
    build: ./frontend
    ports: [ "3000:3000" ]
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: trip_agent
    volumes: [ mysql_data:/var/lib/mysql ]

volumes:
  mysql_data:
```

---

## 11. 扩展与二次开发指南

### 11.1 接入一个新的 LLM

**步骤**：
1. 确认新模型是否兼容 OpenAI 接口格式。如果是，只改 `.env` 中的 `DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`
2. 如果接口格式不同，在 `LLMClient` 中新增适配方法
3. 检查 `response_format: json_object` 新模型是否支持

**需修改的文件**：`llm_client.py`、`.env`、`prompt_builder.py`（必要时）

### 11.2 新增工具调用能力（v2.0）

当想让 Agent 能查询天气、搜索景点、比对机票时，引入 Function Calling。

**步骤**：
1. 在 `agent/` 下新增 `tools/` 目录，每个工具一个文件
2. 每个工具定义遵循 OpenAI Function Calling 格式：name、description、parameters JSON Schema、execute 函数
3. `TripPlannerAgent.handle_message()` 中增加函数调用循环：调用 LLM → 检查 `tool_calls` → 执行工具 → 追加结果 → 再次调用 LLM → 直到无工具调用
4. `PromptBuilder` 中声明可用工具列表

**注意**：工具调用会让每次对话的 LLM 调用次数从 1 次变成 N 次，响应时间显著增加。建议先用 v1.0 验证体验再决定。

---

## 12. 设计决策记录

> **决策 1**：Agent 编排层与路由层分离
> **备选方案**：将 Agent 逻辑直接写在路由函数中
> **选择理由**：Agent 逻辑独立于 HTTP 协议——换入口（CLI、WebSocket、Discord Bot）可复用相同代码
> **可能影响**：文件数增加。好处是可直接 import `planner.py` 做命令行测试

> **决策 2**：意图分类用规则匹配而非 LLM
> **备选方案**：每次用户消息都发给 LLM 做意图分类
> **选择理由**：v1.0 只有 4 种意图，关键词匹配覆盖 90% 场景，省一次 LLM 调用
> **可能影响**：规则匹配有边界情况，极少数误判不影响核心体验

> **决策 3**：行程数据用 JSON 字段存储而非关系表
> **备选方案**：拆成 trips/days/attractions/meals 四张关系表
> **选择理由**：LLM 输出天然是 JSON，字段变化只改 Prompt 不改 schema；MVP 不需要聚合分析
> **可能影响**：未来需统计"热门目的地"时 MySQL JSON 查询性能差，可加 ETL 任务补充

> **决策 4**：前端直连后端，不做 BFF 层
> **备选方案**：Next.js API Routes 转发或 Nginx 反向代理
> **选择理由**：v1.0 用户只有你一个，CORS + localStorage JWT 足够，少一层转发少一个出错环节
> **可能影响**：JWT 在 localStorage 有 XSS 风险，未来上线给他人使用时可迁移到 httpOnly cookie + Nginx

> **决策 5**：开发 SQLite，生产 MySQL
> **备选方案**：全程 MySQL 或全程 SQLite
> **选择理由**：SQLite 开发零配置，`uvicorn` 直接能跑。SQLAlchemy 抽象了差异，切换只改一行连接串
> **可能影响**：需确保所有数据库操作都用 ORM，不写原生 SQL

---

## 13. 待确认事项

- [ ] `plan_data` JSON 的最终字段：需在 Prompt Engineering 阶段迭代调整
- [ ] 前端 UI 的具体样式：建议阶段 5 根据实际体验决定
- [ ] 是否引入 shadcn/ui：如果阶段 3 手写聊天 UI 太耗时再引入
- [ ] 流式输出的实际延迟：需在阶段 3 实测后决定是否需要 loading 动画

---

> **文档元信息**
> 生成日期：2026-07-10
> 生成方式：基于项目描述
> 代码版本/提交：N/A（构思阶段）
> 项目类型：Web 应用（前后端分离）
> 写作模式：交互模式
