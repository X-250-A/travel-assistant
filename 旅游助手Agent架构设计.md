# 旅游助手 Agent 架构设计

> v0.8.0 | 2026-08-09 | FastAPI + Next.js 前后端分离 | DeepSeek 驱动

---

## 1. 项目概述

**Travel Agent** 是一个面向国内游的智能行程规划应用，以多轮对话为核心交互范式。用户用自然语言描述旅行意图（目的地、天数、预算、偏好），Agent 理解需求后通过 **LLM 推理 + 工具调用** 自主编排信息——查询天气、估算交通方案、计算预算——最终生成结构化行程 JSON。

项目定位：**展示 Agentic AI 工程能力的全栈项目**——自定义 Agent 循环、工具编排系统、中间件管道、记忆管理（v0.6.0 规则提取）、推理反思（v0.7.0 ReAct）。

> **架构定位说明**：本项目刻意**不做**多 Agent 协作。单用户单行程、工具面轻量（3 个工具）、一次只产出一个结果，单个 ReAct Agent 完全胜任；多 Agent（Orchestrator + 子 Agent）引入的消息传递与状态协调复杂度，远超它在当前规模下的收益。纵深方向（反思、工具丰富、记忆升级、工程化）的投入产出比更高。

### Agent 特征

| 维度             | 当前实现   | 说明                                                             |
| -------------- | ------ | -------------------------------------------------------------- |
| **对话式交互**      | ✅      | 多轮对话，逐步细化需求                                                    |
| **上下文管理**      | ✅      | Token 感知的滑动窗口，自动裁剪历史消息                                         |
| **意图分类**       | ✅      | LLM 分类 + 关键词 fallback，支持 new_trip / modify_trip / ask_question |
| **工具编排**       | ✅      | Agent 自主决定调用时机，最大 10 轮工具调用循环，自动降级                              |
| **推理反思**       | ✅ v0.7.0 | ReAct 闭环：Thought-Action-Observation，工具结果回填后注入内部反思，自我纠错     |
| **Critic 复盘**   | ✅ v0.8.0 | 第二轮 LLM 质量审查（预算/偏好/可执行性三维度）→ 结构化反馈 → 条件性重生成     |
| **记忆系统**       | ✅ v0.6.0 | 用户偏好跨会话持久化（正则提取 → Redis Hash）；向量语义检索后期规划 |
| **多 Agent 协作** | 🚫 已决策不采用 | 当前规模下单 Agent 更优；后续不纳入路线图，纵深方向取而代之 |

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js 15 前端                          │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────┐   │
│  │ Chat UI  │  │ TripCard  │  │ AuthForm │  │ TripDetail│   │
│  │ SSE 流式 │  │ 行程卡片  │  │ 登录注册 │  │ 行程详情  │  │
│  └──────────┘  └───────────┘  └──────────┘  └───────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST JSON + SSE (Authorization: Bearer)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 后端                              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              中间件管道 (Middleware Pipeline)         │    │
│  │  CORS → JWT Auth Middleware → Rate Limit (Redis 滑动窗口) │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                 │
│  ┌────────────────────────┼──────────────────────────┐      │
│  │          路由层 (Routers)                           │     │
│  │  /api/auth/*    /api/chat    /api/trips/*          │     │
│  └────────────────────────┼──────────────────────────┘      │
│                           │                                 │
│  ┌────────────────────────┼──────────────────────────┐      │
│  │        Agent 编排层 (Agent Orchestration)          │      │
│  │                                                   │      │
│  │  ConversationManager          TripPlannerAgent    │      │
│  │  ┌──────────────┐         ┌───────────────────┐   │      │
│  │  │ 会话状态机     │         │ 感知-决策-执行-反思  │    │        │
│  │  │ 消息历史管理   │         │  ReAct 推理循环     │   │      │
│  │  │ 上下文窗口     │         │                   │    │      │
│  │  │ Token 裁剪    │         │ ① LLM 意图分类     │    │       │
│  │  └──────────────┘         │ ② 工具调用循环     │    │       │
│  │                           │ ③ 内部反思注入     │    │       │
│  │                           │ ④ 流式响应生成     │    │      │
│  │                           │ ⑤ JSON 解析落库    │    │      │
│  │                           └───────────────────┘    │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                 │
│  ┌────────────────────────┼──────────────────────────┐     │
│  │            服务层 (Services)                       │     │
│  │  LLMClient              PromptBuilder              │     │
│  │  ┌──────────────┐     ┌───────────────────┐       │     │
│  │  │ 流式/非流式  │     │ System Prompt     │       │     │
│  │  │ HTTPX 连接池 │     │ 模板管理          │       │     │
│  │  │ Token 计数器 │     │ 上下文拼接        │       │     │
│  │  └──────────────┘     └───────────────────┘       │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                 │
│  ┌────────────────────────┼──────────────────────────┐     │
│  │         工具系统 (Tool Registry)                    │     │
│  │                                                    │     │
│  │  Tool Dataclass → 注册中心 → OpenAI Schema 转换    │     │
│  │  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  │     │
│  │  │  Weather │  │Budget Calc   │  │ Transport   │  │     │
│  │  │  天气查询│  │ 预算估算     │  │ Guiding     │  │     │
│  │  │          │  │              │  │ 交通规划    │  │     │
│  │  └──────────┘  └──────────────┘  └─────────────┘  │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                 │
│  ┌────────────────────────┼──────────────────────────┐     │
│  │            数据层 (Data Layer)                     │     │
│  │  SQLAlchemy 2.0 Async ORM                          │     │
│  │  User / Trip / Message                             │     │
│  │  SQLite (dev) / MySQL 8.0 (prod)                   │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   外部服务                                   │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────────┐    │
│  │ DeepSeek API │  │ 高德地图   │  │ OpenWeatherMap   │    │
│  │ (LLM 推理)   │  │ (驾车路径) │  │ (天气预报)       │    │
│  └──────────────┘  └────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 分层职责

| 层             | 职责                               | 设计原则                               |
| ------------- | -------------------------------- | ---------------------------------- |
| **中间件管道**     | CORS、JWT 鉴权、请求级 user_id 注入       | 每个请求必经的关卡，鉴权逻辑与业务解耦                |
| **路由层**       | HTTP 接入、参数校验、响应序列化               | 薄适配层——只做协议转换，不写业务逻辑                |
| **Agent 编排层** | 意图分类、ReAct 工具循环 + 反思、流式生成、JSON 解析 | 核心决策逻辑，独立于 HTTP，可复用到 CLI/WebSocket |
| **服务层**       | LLM API 封装、Prompt 模板管理           | 与编排层解耦——换模型只改这层                    |
| **工具系统**      | Tool 定义、注册、OpenAI Schema 生成、执行分发 | 可插拔——加工具只加一个文件                     |
| **数据层**       | ORM 实体、异步 CRUD、连接管理              | SQLAlchemy 统一 SQLite/MySQL         |

---

## 3. 技术栈

| 技术                          | 用途        | 选型理由                                       |
| --------------------------- | --------- | ------------------------------------------ |
| **Python 3.14 + FastAPI**   | 后端框架      | 原生 async/await、Pydantic 类型校验、自动 OpenAPI 文档 |
| **Next.js 15 (App Router)** | 前端框架      | React Server Components、App Router 文件约定路由  |
| **React 19 + TypeScript**   | 前端语言      | 类型安全，组件化                                   |
| **Tailwind CSS 4**          | 样式方案      | 原子化 CSS，自定义 Design Tokens                  |
| **DeepSeek V4 (Flash)**     | LLM 推理    | 中文能力强、兼容 OpenAI SDK、支持 Function Calling    |
| **SQLAlchemy 2.0 (async)**  | ORM       | 原生 async、SQLite/MySQL 统一抽象                 |
| **SQLite (aiosqlite)**      | 开发数据库     | 零配置、文件级、随项目走                               |
| **MySQL 8.0 (aiomysql)**    | 生产数据库     | Docker Compose 一键切换                        |
| **httpx**                   | HTTP 客户端  | 异步、连接池、超时控制，调用高德等外部 API                    |
| **tiktoken**                | Token 计数器 | OpenAI 兼容编码，精确控制上下文窗口                      |
| **bcrypt + python-jose**    | 认证        | 密码哈希 + JWT 签发/验证                           |
| **Docker + Compose**        | 部署        | backend + frontend + mysql 三服务编排           |

---

## 4. 核心设计

### 4.1 Agent 推理循环（ReAct）

TripPlannerAgent 的核心流程——**感知 → 决策 → 执行 → 观察 → 反思** 循环（v0.7.0 起为完整 ReAct）：

```
用户输入
  │
  ▼
┌──────────────┐     LLM + response_format=json_object
│ ① 意图分类   │─────────────────────────────────────►  intent: new_trip
│ llm_classify │                                       / modify_trip
│ _intent()    │  ▼ 关键词匹配 fallback                 / ask_question
└──────────────┘
  │
  ├─ new_trip ──────────────────────────────────┐
  │                                              ▼
  │                              ┌──────────────────────────┐
  │                              │ ② ReAct 工具循环           │
  │                              │ _generate_plan()         │
  │                              │                          │
  │                              │ while tool_round < 10:   │
  │                              │   LLM.chat(tools=...)    │
  │                              │   if no tool_calls:      │
  │                              │     → 流式输出 退出        │
  │                              │   for each tool_call:    │
  │                              │     result = execute()   │
  │                              │     append tool msg      │
  │                              │     thoughts.append(…)   │
  │                              │   → 注入 [内部推理]        │
  │                              │   （基于已掌握信息自我评估， │
  │                              │     决定停止 or 补调）     │
  │                              │   tool_round++           │
  │                              │                          │
  │                              │ tool_round >= 10:        │
  │                              │   → 强制流式输出（兜底）    │
  │                              └──────────────────────────┘
  │
  ├─ modify_trip ───────────────┐
  │                              ▼
  │               ┌─────────────────────────┐
  │               │ ③ 反馈式调整             │
  │               │ _apply_feedback()        │
  │               │ 当前行程 JSON + 用户要求  │
  │               │ → 局部修改 → 流式输出    │
  │               └─────────────────────────┘
  │
  └─ ask_question ──────────────┐
                                 ▼
                  ┌─────────────────────────┐
                  │ ④ 闲聊分流               │
                  │ gossip()                  │
                  │ 不涉及行程，自由对话      │
                  └─────────────────────────┘
  │
  ▼
┌──────────────┐
│ ⑤ 结果处理   │
│ 分离文本/JSON │
│ plan_data 落库│
│ 保存 AI 回复  │
└──────────────┘
```

**反思（Thought）如何生效**：模型在并行调用多个工具后，每轮工具结果回填 `messages`，同时在调用下一轮 LLM 前注入一条 `[内部推理]` assistant 消息——模型基于全部已掌握信息评估"是否已满足用户需求"，满足则直接组织回答，不满足则针对性补调。`thoughts` 列表保留最近 3 轮观察摘要（截断长结果控 token）。实机验证：模型第一轮并行查天气/预算/交通，反思发现舒适档预算超支，第二轮**只补调经济档重算**，最终收敛输出行程 JSON。

### 4.1.1 记忆系统（v0.6.0，规则提取）

`memory/preferences.py` 用正则从对话中提取结构化偏好（饮食忌口、预算上限、出行限制、节奏），写入 Redis Hash `user:preferences:{user_id}`（TTL 30 天），通过 `PromptBuilder.render_preferences()` 注入 System Prompt。

**设计决策：规则而非向量嵌入**——偏好本身是低熵结构化信息（"不吃辣""预算3000元"），正则精确、零成本、可解释；向量语义检索留待 v0.9.0 用于非结构化记忆。

**关键安全机制**：

- **工具调用上限**：最多 10 轮调用，防止无限循环消耗 token
- **LLM 意图分类 fallback**：LLM 调用失败时降级到关键词匹配，保证服务可用
- **JSON 解析三级回退**：````json` 标记 → ```` ` 标记 → 正则匹配裸 JSON

### 4.2 工具系统：可插拔注册中心

工具系统是本项目的架构亮点——每个工具是独立的 `.py` 文件，通过统一的 `Tool` dataclass 定义，注册到中心后自动转换为 OpenAI Function Calling 格式。

**设计演进**：

| 版本     | 方案                    | 问题                                                |
| ------ | --------------------- | ------------------------------------------------- |
| v0.2.0 | 硬编码字典                 | 每个工具写一套重复的定义结构                                    |
| v0.4.0 | Tool dataclass + 注册中心 | `Tool.openai_schema()` 统一生成，`execute_tool()` 统一调度 |

**`Tool` 数据类**（`backend/app/tools/base.py`）：

```python
@dataclass
class Tool:
    name: str                              # 工具唯一标识
    description: str                       # LLM 选择工具时参考
    parameters: dict[str, Any]             # JSON Schema properties
    required: list[str]                    # 必填参数列表
    handler: Callable[..., Awaitable[str]] # 异步执行函数

    def openai_schema(self) -> dict:
        """一键生成 OpenAI function-calling 兼容格式"""
```

**当前工具清单**：

| 工具                  | 文件                     | 能力                           | 外部依赖                      |
| ------------------- | ---------------------- | ---------------------------- | ------------------------- |
| `weather`           | `weather.py`           | 查询任意城市实时天气/温度/湿度/风力          | OpenWeatherMap API        |
| `budget_calculate`  | `budget_calculate.py`  | 根据天数/人数/档次（经济/舒适/豪华）估算旅行预算分项 | 纯规则引擎                     |
| `transport_guiding` | `transport_guiding.py` | 跨城交通方案：距离/耗时/方式推荐/费用         | 高德地图 API + Haversine 距离降级 |

**架构价值**：要加新工具（如景点查询），只需在 `tools/` 下新建文件、定义 `Tool` 实例、在 `ALL_TOOLS` 列表追加一行——`__init__.py`、`planner.py` 不需要任何改动。这是面试中最容易展开讲的扩展性设计。

### 4.3 中间件管道

请求经过两层中间件的顺序处理：

```
Request → CORS Middleware → JWT Auth Middleware → Router → ...

                          ┌ 白名单放行：
                          │ /, /docs, /redoc,
                          │ /openapi.json,
                          │ /api/auth/register,
                          │ /api/auth/login
                          │
                          └ 其他路径：
                              ① 提取 Authorization header
                              ② 校验 Bearer 格式
                              ③ JWT decode + 签名验证
                              ④ 提取 user_id → request.state.user_id
                              ⑤ 失败 → 401 JSONResponse
```

**设计考量**：JWT 验证放在中间件而非 `Depends()` 中，因为：

- 鉴权是横切关注点，应该独立于业务逻辑
- 中间件在路由执行前拦截，无效请求不进入业务层
- `get_current_user` 只需从 `request.state.user_id` 取用户，不再重复解析 token

### 4.4 上下文管理

`ConversationManager` 管理每次对话的消息历史和状态机：

```
状态流转：
  IDLE → PLANNING → CONFIRMING → DONE

上下文窗口（Token 感知裁剪）：
  全部消息 → 按时间降序排列 → 从尾部向前截取
  → 累计 token < max_tokens → 返回裁剪后的消息列表
```

每个消息即时写入数据库，同时缓存在内存 `history_cache` 中。上下文裁剪只删最早的、保留最新的——保证最近的对话轮次始终完整。

---

## 5. 数据模型

### 5.1 ER 图

```
User (用户)
  ├── id: int (PK)
  ├── username: str (unique)
  ├── hashed_password: str (bcrypt)
  └── created_at: datetime

     │ 1:N
     ▼
Trip (行程)
  ├── id: int (PK)
  ├── user_id: int (FK → User)
  ├── title: str
  ├── plan_data: JSON (LLM 生成的结构化行程)
  ├── status: "draft" | "confirmed"
  ├── created_at: datetime
  └── updated_at: datetime

     │ 1:N
     ▼
Message (消息)
  ├── id: int (PK)
  ├── trip_id: int (FK → Trip)
  ├── role: "user" | "assistant" | "system"
  ├── content: text
  └── created_at: datetime
```

### 5.2 plan_data JSON 结构

```json
{
  "destination": "成都",
  "duration": 3,
  "budget": 3000,
  "style": ["美食", "人文"],
  "overview": "三日行程涵盖...",
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
  "overall_tips": "6月成都多雨，建议带伞..."
}
```

### 设计决策：JSON 字段 vs 关系表

| 方案          | 优点                            | 缺点                              | 本项目选择 |
| ----------- | ----------------------------- | ------------------------------- | ----- |
| **JSON 字段** | LLM 产出直接存，零转换；字段弹性变化不改 schema | 不支持 SQL 级联查询                    | ✅ 采用  |
| **多张关系表**   | 支持复杂 SQL 分析                   | LLM JSON → 多条 INSERT 的映射逻辑复杂且脆弱 | ❌     |

本项目是行程生成工具而非数据分析平台——JSON 字段是正确的选择。

---

## 6. 关键技术决策

> **决策 1**：Agent 编排层与路由层分离
> **选择**：`planner.py` 不依赖 FastAPI Request 对象，通过 Python 原生类型交互
> **收益**：Agent 可独立测试（import 后直接调方法），可换入口（CLI/WebSocket/Discord Bot）

> **决策 2**：意图分类：LLM + 规则双通道
> **选择**：优先 LLM 分类（`response_format: json_object`, temperature=0），失败时降级到关键词匹配
> **收益**：LLM 处理模糊表达（"有点贵"→modify_trip），规则兜底保证可用性，只多一次轻量 API 调用

> **决策 3**：工具调用循环上限 = 10 轮
> **选择**：硬上限 + 日志告警 + 强制流式输出兜底
> **收益**：防止模型陷入"调用→不满意→再调用"的死循环，避免单次会话消耗数千 token

> **决策 4**：JWT 验证放中间件，不放 Depends
> **选择**：`jwt_middleware` 在路由前拦截，`get_current_user` 从 `request.state` 读取
> **收益**：鉴权横切逻辑独立；无效请求不进入业务层；Depends 链更简洁

> **决策 5**：工具无状态，按需调用
> **选择**：每个工具只接收参数、返回字符串，不持有对话上下文
> **收益**：工具函数可独立测试、独立替换；LLM 通过 tool result 感知上下文，不需要工具侧维护状态

> **决策 6**：SQLite 开发，MySQL 生产
> **选择**：SQLAlchemy async 抽象层 + Docker Compose 切换
> **收益**：开发零配置；所有操作走 ORM 保证可移植性

> **决策 7**：反思（Thought）作为独立消息注入，而非混入输出流
> **选择**：工具结果回填后，注入 `[内部推理]` assistant 消息给模型消化，绝不 `yield` 到前端
> **收益**：模型基于全量工具结果自我纠错（实机验证降档重算）；`thinking` 事件与 `token` 事件分流，前端打字机不受内部推理污染。这是 ReAct 区别于"纯工具调用"的关键——模型在**决策层**反思，而非在**输出层**展示思考过程

---

## 7. 前端设计系统

v0.4.0 建立了完整的 Design Token 体系，彻底摆脱组件库默认风格：

| 令牌                | 值                            | 用途                |
| ----------------- | ---------------------------- | ----------------- |
| `--color-primary` | `#f97316` (Orange 500)       | 主操作按钮、强调色         |
| `--color-accent`  | `#0ea5e9` (Sky 500)          | 辅助强调、链接           |
| `--color-surface` | `#fafaf9` (Stone 50)         | 卡片底色              |
| `--color-text`    | `#1c1917` (Stone 900)        | 正文                |
| 字体                | Noto Sans SC + Noto Serif SC | Google Fonts 中文字体 |
| 背景                | 暖色四段渐变                       | 奶油→桃子→粉紫→天空蓝      |

**UI 组件体系**：Button（4 变体 + Loading 态）→ Card（3 风格 + 3 内边距）→ Loading（自定义文本）→ Chat（空状态引导页 + 流式逐字渲染）→ Trip（状态标签 + 指标行 + Glass 卡片）

---

## 8. 开发路线

### 已完成 (v0.1.0 – v0.7.0)

| 版本     | 里程碑                                     |
| ------ | --------------------------------------- |
| v0.1.0 | 项目骨架、用户认证（JWT + bcrypt）、ORM 建表          |
| v0.2.0 | DeepSeek 集成、Tool Calling 机制、天气预报工具      |
| v0.3.0 | LLM 意图分类、闲聊分流、工具调用循环防护                  |
| v0.4.0 | 前端设计系统重构、后端工具注册中心、预算计算工具、交通规划工具、JWT 中间件 |
| v0.5.0 | Redis 集成：Token 黑名单 + 滑动窗口限流 + 天气缓存       |
| v0.6.0 | Agent 记忆系统（偏好提取 + 跨会话持久化）+ 行程确认/编辑接后端  |
| v0.7.0 | ReAct 推理循环（Thought-Action-Observation）+ 反思机制   |
| v0.8.0 | 行程方案 Critic 复盘（自评自纠）—— 二轮审查 + 条件重生成     |

### 规划中 (v0.9.0 → v1.0.0)

> **路线调整（2026-08-07）**：放弃多 Agent 协作方向（当前规模下大材小用），改为**纵深**路线——在单 Agent 内把「反思、工具、记忆、工程化」做深，每个版本都能独立讲述一个可面试的工程点。

| 版本         | 计划                         | 技术关键词 / 面试亮点                          |
| ---------- | -------------------------- | ---------------------------------------- |
| **v0.9.0** | 记忆升级：向量语义检索 + 景点查询工具       | 向量嵌入 + 相似度召回；高德 POI API 接入新工具         |
| **v1.0.0** | 测试覆盖、E2E、Docker 生产部署       | pytest + Playwright E2E；容器化 + CI/CD 流水线   |

---

## 9. 安全设计

| 维度       | 方案                                          |
| -------- | ------------------------------------------- |
| **密码存储** | bcrypt (passlib)，不存明文                       |
| **传输认证** | JWT (HS256)，7 天过期，Authorization: Bearer 头传递 |
| **接口保护** | 全局 JWT 中间件，白名单放行公开路径，其余拦截                   |
| **密码时效** | Redis 黑名单主动吊销（jti）· refresh token 规划中          |
| **速率限制** | Redis 滑动窗口（Sorted Set），register/login 已接入        |

---

## 10. 部署

```yaml
# docker-compose.yml
services:
  backend:    # FastAPI + uvicorn, port 8000
  frontend:   # Next.js (standalone), port 3000
  mysql:      # MySQL 8.0, port 3306 (生产)
  redis:      # Redis 7 (v0.5.0 引入)
```

开发环境：`uvicorn --reload` + `npm run dev`，SQLite 文件数据库，零外部依赖即可运行。

---

> **文档元信息**
> 版本：v0.8.0 | 更新日期：2026-08-09 | 代码版本：待提交
> 对应 API 文档：旅游助手AgentAPI接口规范.md
