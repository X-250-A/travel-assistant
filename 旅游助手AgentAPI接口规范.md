# 旅游助手 Agent API 接口规范

> v0.9.0 | Base URL: `http://localhost:8000` | Protocol: REST JSON + SSE Streaming

---

## 1. 通用约定

### 1.1 请求格式

- **Content-Type**: `application/json`
- **认证方式**: `Authorization: Bearer <access_token>`（注册/登录除外）
- **字符编码**: UTF-8

### 1.2 认证体系

使用 JWT (HS256) 无状态认证。流程：

```
注册 → 登录获取 token → 后续请求携带 Authorization: Bearer <token>
                                │
                                ├─ JWT Middleware 拦截
                                ├─ 白名单放行（/docs, /api/auth/*）
                                ├─ 解码验证 → request.state.user_id
                                └─ get_current_user → 查 DB → User 对象
```

JWT 默认 **7 天过期**，过期后需重新登录。

### 1.3 响应格式

**成功响应**：

```json
{
  "data": { ... },
  "message": "ok"
}
```

**错误响应**：

```json
{
  "detail": "错误描述"
}
```

### 1.4 HTTP 状态码

| 状态码 | 含义 | 触发场景 |
|--------|------|---------|
| 200 | 成功 | GET 请求、PATCH 请求 |
| 201 | 创建成功 | POST /api/auth/register |
| 400 | 请求参数错误 | 用户名已存在 |
| 401 | 未认证 | JWT 缺失/无效/过期、格式错误 |
| 403 | 无权限 | 访问不属于自己的行程 |
| 404 | 资源不存在 | 行程 ID 无效 |
| 422 | 请求体验证失败 | Pydantic 字段校验失败 |
| 429 | 请求过多 | 速率限制（滑动窗口） |
| 500 | 服务器内部错误 | 未捕获异常 |

---

## 2. 数据模型

### 2.1 枚举值

| 枚举 | 可选值 | 说明 |
|------|--------|------|
| `TripStatus` | `draft`, `confirmed` | 行程状态 |
| `MessageRole` | `user`, `assistant`, `system` | 消息发送者 |
| `IntentType` | `new_trip`, `modify_trip`, `ask_question`, `unclear` | Agent 意图分类结果 |
| `MealType` | `breakfast`, `lunch`, `dinner`, `snack` | 用餐类型 |

### 2.2 核心类型

#### User

```typescript
interface User {
  id: number;
  username: string;
  created_at: string;  // ISO 8601
}
```

#### Trip

```typescript
interface Trip {
  id: number;
  user_id: number;
  title: string;                      // e.g. "成都三日美食之旅"
  plan_data: PlanData | null;         // null = 尚未生成行程
  status: "draft" | "confirmed";
  created_at: string;
  updated_at: string;
}
```

#### PlanData

```typescript
interface PlanData {
  destination: string;                // 目的地城市
  duration: number;                   // 行程天数
  budget: number;                     // 预估预算（元）
  style: string[];                    // 风格标签 e.g. ["美食", "人文"]
  overview: string;                   // 行程概述 1-2 段
  days: DayPlan[];                    // 每日计划
  overall_tips: string;               // 综合贴士
}

interface DayPlan {
  day: number;                        // 第 N 天 (1-based)
  date: string | null;                // 具体日期，null=待定
  theme: string;                      // 当日主题
  attractions: Attraction[];          // 景点/活动
  meals: Meal[];                      // 用餐推荐
}

interface Attraction {
  name: string;
  type: string;                       // "景点" | "餐饮" | "购物" | ...
  duration_minutes: number;
  cost_yuan: number;                  // 0 = 免费
  tips: string;
  transport_from_previous: string | null;  // 交通方式，首个景点为 null
}

interface Meal {
  meal_type: "breakfast" | "lunch" | "dinner" | "snack";
  suggestion: string;                 // 推荐描述
  location_near: string;              // 附近地标
}
```

#### Message

```typescript
interface Message {
  id: number;
  trip_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}
```

---

## 3. 接口详述

### 3.1 认证模块

#### `POST /api/auth/register` — 用户注册

无需认证。

**Request Body**：

```json
{
  "username": "zhangsan",
  "password": "mypassword123"
}
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| `username` | string | ✅ | 3-30 字符，唯一 |
| `password` | string | ✅ | 6-100 字符 |

**Response (201)**：

```json
{
  "id": 1,
  "username": "zhangsan",
  "created_at": "2026-07-30T12:00:00"
}
```

**错误**：
- `400` — `{"detail": "用户名已存在"}`
- `422` — Pydantic 字段校验失败

---

#### `POST /api/auth/login` — 用户登录

无需认证。

**Request Body**：

```json
{
  "username": "zhangsan",
  "password": "mypassword123"
}
```

**Response (200)**：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**错误**：
- `401` — `{"detail": "用户名或密码错误"}`

---

#### `GET /api/auth/me` — 获取当前用户

**需要认证**。

**Headers**：`Authorization: Bearer <token>`

**Response (200)**：

```json
{
  "id": 1,
  "username": "zhangsan",
  "created_at": "2026-07-30T12:00:00"
}
```

---

### 3.2 对话模块（核心）

#### `POST /api/chat` — 发送消息，接收 Agent 流式响应

**需要认证**。整个系统的核心端点。接收用户消息，经过 Agent 流水线（意图分类 → 工具调用循环 → LLM 生成），以 SSE 流式返回。

**Request Body**：

```json
{
  "message": "帮我规划一个杭州三日游，预算2000，喜欢自然风光",
  "trip_id": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message` | string | ✅ | 用户消息 |
| `trip_id` | int \| null | 否 | 已有行程 ID，不传则自动创建新行程 |

**Response**：`Content-Type: text/event-stream`

##### SSE 事件类型

流式响应由多个 SSE 事件组成，每个事件格式为 `data: <JSON>\n\n`：

**`token` 事件** — 逐字文本块（打字机效果），多次发送：

```
data: {"type":"token","content":"好"}

data: {"type":"token","content":"的，我为您规划..."}

data: {"type":"token","content":"\n\n## 第一天：西湖经典环湖"}
```

**`thinking` 事件** — Agent 内部过程提示（v0.7.0 起）：工具调用/内部反思/质量审查进行中，**不进入消息文本**，前端渲染为"🤔 Agent 正在思考"气泡：

```
data: {"type":"thinking","content":"我现在要使用 get_weather, search_poi 工具查询信息..."}

data: {"type":"thinking","content":"正在对行程方案做质量审查…"}
```

**`done` 事件** — 流结束，携带 trip_id 供前端关联：

```
data: {"type":"done","data":{"trip_id":42}}
```

**`error` 事件** — 异常信息：

```
data: {"type":"error","detail":"行程生成失败，请重试"}
```

##### Agent 内部流程

```
POST /api/chat
  │
  ├─ ① 找到或创建 Trip
  │     trip_id 有值 → 查 DB 验证归属
  │     trip_id null → 新增 Trip (title="新行程")
  │
  ├─ ② 初始化 ConversationManager（状态机 + 历史消息）
  │
  ├─ ③ TripPlannerAgent.handle_message()
  │     ├─ 0. 记忆加载：规则偏好（Redis Hash）+ 向量记忆召回（相似度 top-k，可用时）
  │     ├─ 0.5 向量记忆保存：LLM 抽取事实 → bge-m3 嵌入 → Redis List（全分支覆盖）
  │     ├─ LLM 意图分类 (new_trip / modify_trip / ask_question)
  │     ├─ 生成行程：ReAct 工具调用循环（≤10 轮）+ 流式输出
  │     ├─ 调整行程：当前 JSON + 反馈 → LLM 局部修改
  │     ├─ 闲聊：直接流式对话
  │     └─ 4.5 Critic 质量审查（v0.8.0）：不达标 → 带 issues 轻量重生成
  │
  ├─ ④ JSON 解析 + plan_data 落库
  │
  └─ ⑤ SSE 流式返回每条 token / thinking 事件
```

##### 前端消费示例

```typescript
async function sendMessage(message: string, tripId: number | null, token: string) {
  const res = await fetch("http://localhost:8000/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message, trip_id: tripId }),
  });

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const event = JSON.parse(line.slice(6));

      switch (event.type) {
        case "token":
          appendToChat(event.content);      // 累积渲染
          break;
        case "thinking":
          setThinking(event.content);        // 渲染"🤔 正在思考"气泡（不进入消息文本）
          break;
        case "done":
          setCurrentTripId(event.data.trip_id);  // 记住行程 ID
          finishStreaming();
          break;
        case "error":
          showError(event.detail);
          break;
      }
    }
  }
}
```

##### 错误

- `401` — `{"detail": "未提供认证信息"}`
- `403` — `{"detail": "无权限访问该行程"}`（trip 不属于当前用户）
- `404` — `{"detail": "行程不存在"}`
- `422` — 请求体字段校验失败

---

### 3.3 行程管理

#### `GET /api/trips` — 行程列表

**需要认证**。返回当前用户的所有行程，按更新时间倒序。

**Query Parameters**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | integer | 否 | 1 | 页码 |
| `page_size` | integer | 否 | 100 | 每页数量 |

**Response (200)**：

```json
{
  "trips": [
    {
      "id": 42,
      "user_id": 1,
      "title": "杭州三日自然之旅",
      "status": "confirmed",
      "created_at": "2026-07-30T10:00:00",
      "updated_at": "2026-07-30T10:05:00"
    },
    {
      "id": 41,
      "user_id": 1,
      "title": "成都三日美食之旅",
      "status": "draft",
      "created_at": "2026-07-29T14:00:00",
      "updated_at": "2026-07-29T14:30:00"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 100
}
```

> **注意**：列表不包含 `plan_data`（数据量大），详情需单独请求。

---

#### `GET /api/trips/{trip_id}` — 行程详情

**需要认证**。返回完整行程信息，包含 `plan_data`。

**Response (200)**：

```json
{
  "id": 42,
  "user_id": 1,
  "title": "杭州三日自然之旅",
  "plan_data": {
    "destination": "杭州",
    "duration": 3,
    "budget": 2000,
    "style": ["自然风光"],
    "overview": "三日行程涵盖西湖经典与新西湖秘境...",
    "days": [
      {
        "day": 1,
        "date": null,
        "theme": "西湖经典环湖",
        "attractions": [
          {
            "name": "断桥残雪",
            "type": "景点",
            "duration_minutes": 60,
            "cost_yuan": 0,
            "tips": "清晨前往游客较少",
            "transport_from_previous": null
          }
        ],
        "meals": [
          {
            "meal_type": "lunch",
            "suggestion": "楼外楼东坡肉，人均 80 元",
            "location_near": "孤山路"
          }
        ]
      }
    ],
    "overall_tips": "杭州地铁覆盖主要景点，6月多雨建议带伞"
  },
  "status": "confirmed",
  "created_at": "2026-07-30T10:00:00",
  "updated_at": "2026-07-30T10:05:00"
}
```

**错误**：
- `401` — 未认证
- `403` — 无权访问（行程不属于当前用户）
- `404` — 行程不存在

---

#### `PATCH /api/trips/{trip_id}` — 更新行程

**需要认证**。支持修改 `title` 或 `status`（如 `draft` → `confirmed`）。支持部分更新——只传要改的字段。

**Request Body**：

```json
{
  "title": "杭州三日深度游",
  "status": "confirmed"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 否 | 新标题，不传则不改 |
| `status` | string | 否 | `draft` / `confirmed`，不传则不改 |

**Response (200)**：返回更新后的完整 Trip 对象。

**错误**：同详情接口。

---

#### `DELETE /api/trips/{trip_id}` — 删除行程

**需要认证**。删除行程同时级联删除其关联的所有消息。

**Response (200)**：

```json
{
  "data": null,
  "message": "行程已删除"
}
```

**错误**：同详情接口。

---

#### `GET /api/trips/{trip_id}/messages` — 行程对话历史

**需要认证**。返回指定行程的所有对话消息，按时间升序排列。

**Response (200)**：

```json
[
  {
    "id": 1001,
    "trip_id": 42,
    "role": "user",
    "content": "帮我规划杭州三日游",
    "created_at": "2026-07-30T10:00:00"
  },
  {
    "id": 1002,
    "trip_id": 42,
    "role": "assistant",
    "content": "好的，为您规划了杭州三日自然风光之旅...",
    "created_at": "2026-07-30T10:00:15"
  }
]
```

> **用途**：前端加载已有行程时，重新渲染完整的对话历史。

---

### 3.4 健康检查

#### `GET /` — 根路径

无需认证。

**Response (200)**：

```json
{
  "message": "Hello World"
}
```

---

## 4. 接口总览

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/` | 否 | 根路径 |
| POST | `/api/auth/register` | 否 | 用户注册 |
| POST | `/api/auth/login` | 否 | 用户登录 |
| GET | `/api/auth/me` | 是 | 当前用户信息 |
| POST | `/api/chat` | 是 | **核心**：发送消息（SSE 流式） |
| GET | `/api/trips` | 是 | 行程列表（分页） |
| GET | `/api/trips/{id}` | 是 | 行程详情（含 plan_data） |
| PATCH | `/api/trips/{id}` | 是 | 更新行程标题/状态 |
| DELETE | `/api/trips/{id}` | 是 | 删除行程（级联删消息） |
| GET | `/api/trips/{id}/messages` | 是 | 行程对话历史 |

---

## 5. Agent 工具调用（隐式）

以下工具由 Agent 在对话中**自动调用**，前端无需感知。用户只需要自然对话，Agent 自主决定调用时机。

| 工具名 | 触发场景示例 | 返回内容 |
|--------|-------------|---------|
| `weather` | "成都下周天气怎么样" | 温度/湿度/风力/天气描述 |
| `budget_calculate` | "预算大概多少" | 住宿/餐饮/交通/门票/其他分项 |
| `transport_guiding` | "北京到杭州怎么去" | 距离/耗时/推荐方式/费用估算 |
| `search_poi` | "杭州有哪些必去景点" | 景点名称/地址/评分/人均消费（高德 POI，v0.9.0） |

**工具调用上限**：单次对话最多 10 轮工具调用，超过后强制生成回复（防止死循环）。

---

## 6. 前端错误处理指南

```typescript
// 全局 fetch 拦截器
function handleApiError(status: number, detail: string) {
  switch (status) {
    case 401:
      localStorage.removeItem("token");
      router.push("/login");
      break;
    case 403:
      showToast("无权访问该资源");
      break;
    case 422:
      // Pydantic 校验错误，解析字段级提示
      showFieldErrors(detail);
      break;
    case 429:
      // 速率限制（v0.5.0）
      showToast("请求过快，请稍候");
      break;
    case 500:
      showToast("服务器异常，请稍后重试");
      break;
  }
}

// SSE 流中的 error 事件处理
function handleSSEError(event: { type: "error"; detail: string }) {
  showChatError(event.detail);     // 在聊天区显示错误提示
  // 不丢失已生成的部分内容
  // 用户可重新发送或修改需求
}
```

---

## 7. 环境变量

服务端通过 `.env` 文件配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | 数据库连接串 | `sqlite+aiosqlite:///./trip_agent.db` |
| `SECRET_KEY` | JWT HS256 签名密钥 | 随机字符串（`openssl rand -hex 32`） |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-xxx` |
| `DEEPSEEK_BASE_URL` | DeepSeek 接口地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-v4-flash` |
| `WEATHER_API_KEY` | OpenWeatherMap Key | 用于天气工具 |
| `AMAP_API_KEY` | 高德地图 API Key | 用于交通规划工具 |
| `LLM_CONNECT_TIMEOUT` | LLM 连接超时（秒）| `10.0` |
| `LLM_READ_TIMEOUT` | LLM 读取超时（秒）| `45.0` |
| `LLM_REQUEST_TIMEOUT` | LLM 请求总超时（秒）| `90.0` |
| `CORS_ORIGINS` | 允许的跨域来源 | `http://localhost:3000` |
| `REDIS_URL` | Redis 连接串（黑名单/限流/缓存/偏好/向量记忆） | `redis://192.168.126.128:6379/0` |
| `REDIS_TOKEN_BLACKLIST_DB` | JWT 黑名单所在 Redis DB | `1` |
| `RATE_LIMIT_REQUESTS` | 滑动窗口限流阈值（次/窗） | `30` |
| `RATE_LIMIT_WINDOW` | 限流窗口（秒） | `60` |
| `WEATHER_CACHE_TTL` | 天气缓存时长（秒） | `3600` |
| `PERMANENT_SESSION_LIFETIME` | 用户偏好等长期数据 TTL（秒） | `2592000` |
| `MAX_CONTEXT_TOKENS` | 上下文窗口 Token 上限（历史裁剪阈值） | `6000` |
| `CRITIC_ENABLED` | Critic 质量审查总开关（v0.8.0） | `True` |
| `CRITIC_MAX_REGENERATE` | 审查不达标最大重生成次数（防死循环） | `1` |
| `SILICONFLOW_API_KEY` | SiliconFlow Key，向量记忆嵌入（v0.9.0） | 无则不启用向量记忆 |
| `SILICONFLOW_BASE_URL` | 嵌入服务地址 | `https://api.siliconflow.cn/v1` |
| `SILICONFLOW_EMBEDDING_MODEL` | 嵌入模型 | `BAAI/bge-m3` |
| `MEMORY_TOPK` | 向量记忆召回条数上限 | `3` |
| `MEMORY_SIM_THRESHOLD` | 向量记忆召回相似度阈值 | `0.45` |
| `POI_CACHE_TTL` | POI 景点查询缓存时长（秒） | `86400` |

---

> **文档元信息**
> 版本：v0.9.0 | 更新日期：2026-08-17 | 代码版本：78f2b26（POI 已提交；向量记忆部分为工作区在制品）
> 对应架构文档：旅游助手Agent架构设计.md
