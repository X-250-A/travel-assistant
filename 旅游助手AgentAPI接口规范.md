# 旅游助手 Agent API 接口规范

> v1.0 | 基准 URL: `http://localhost:8000` | 协议: REST JSON + SSE 流式

---

## 1. 通用约定

### 1.1 请求格式

- Content-Type: `application/json`（除注册/登录外，所有请求必须携带 JWT）
- 认证方式: `Authorization: Bearer <access_token>`
- 字符编码: UTF-8

### 1.2 响应格式

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

### 1.3 HTTP 状态码

| 状态码 | 含义                   |
| --- | -------------------- |
| 200 | 请求成功                 |
| 201 | 创建成功                 |
| 400 | 请求参数错误               |
| 401 | 未认证（JWT 缺失或无效）       |
| 403 | 无权限（访问了不属于自己的资源）     |
| 404 | 资源不存在                |
| 422 | 请求体验证失败（Pydantic 校验） |
| 500 | 服务器内部错误              |

### 1.4 认证说明

除注册和登录外，所有接口都要在 Header 中携带 JWT：

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

JWT 默认 7 天过期。过期后需重新登录获取新 Token。

---

## 2. 数据模型

### 2.1 枚举值

| 枚举               | 可选值                                                  | 说明       |
| ---------------- | ---------------------------------------------------- | -------- |
| `TripStatus`     | `draft`, `confirmed`                                 | 行程状态     |
| `MessageRole`    | `user`, `assistant`, `system`                        | 消息角色     |
| `IntentType`     | `new_trip`, `modify_trip`, `ask_question`, `unclear` | 用户意图     |
| `AttractionType` | `景点`, `餐饮`, `购物`, `交通枢纽`, `其他`                       | 行程中的地点类型 |
| `MealType`       | `breakfast`, `lunch`, `dinner`, `snack`              | 用餐类型     |

### 2.2 核心数据结构

#### User

```typescript
interface User {
  id: string;           // UUID
  username: string;     // 唯一用户名
  created_at: string;   // ISO 8601
}
```

#### Trip

```typescript
interface Trip {
  id: string;            // UUID
  user_id: string;       // 所属用户 UUID
  title: string;         // 如 "成都三日美食之旅"
  plan_data: PlanData | null;  // 完整行程 JSON，null 表示尚未生成
  status: "draft" | "confirmed";
  created_at: string;    // ISO 8601
  updated_at: string;    // ISO 8601
}
```

#### PlanData

```typescript
interface PlanData {
  destination: string;       // 目的地城市
  duration: number;          // 行程天数
  budget: number;            // 预算（元）
  style: string[];           // 风格标签，如 ["美食", "人文", "自然风光"]
  overview: string;          // 行程概述（1-2 段话）
  days: DayPlan[];           // 每日计划
  overall_tips: string;      // 综合旅行贴士
}

interface DayPlan {
  day: number;               // 第几天，从 1 开始
  date: string | null;       // 具体日期，null 表示待定
  theme: string;             // 当日主题，如 "市区人文初探"
  attractions: Attraction[]; // 当日景点/活动列表
  meals: Meal[];             // 当日用餐推荐
}

interface Attraction {
  name: string;                    // 名称
  type: string;                    // 类型：景点、餐饮等
  duration_minutes: number;        // 建议停留时长（分钟）
  cost_yuan: number;               // 费用（元），0 表示免费
  tips: string;                    // 游玩提示
  transport_from_previous: string | null;  // 从上一个景点过来的交通方式，首个景点为 null
}

interface Meal {
  meal_type: string;         // breakfast / lunch / dinner / snack
  suggestion: string;        // 用餐推荐描述
  location_near: string;     // 附近位置
}
```

#### Message

```typescript
interface Message {
  id: string;              // UUID
  trip_id: string;         // 所属行程 UUID
  role: "user" | "assistant" | "system";
  content: string;         // 消息文本
  created_at: string;      // ISO 8601
}
```

---

## 3. 接口列表

### 3.1 健康检查

```
GET /api/health
```

无需认证。用于验证后端服务是否正常运行。

**响应示例**：

```json
{
  "status": "ok"
}
```

---

### 3.2 用户认证

#### 3.2.1 注册

```
POST /api/auth/register
```

**请求体**：

```json
{
  "username": "zhangsan",
  "password": "mypassword123"
}
```

| 字段         | 类型     | 必填  | 说明             |
| ---------- | ------ | --- | -------------- |
| `username` | string | 是   | 用户名，3-30 字符，唯一 |
| `password` | string | 是   | 密码，6-100 字符    |

**成功响应 (201)**：

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "zhangsan",
    "created_at": "2026-07-10T12:00:00Z"
  },
  "message": "注册成功"
}
```

**错误示例**：

- 用户名已存在 (400): `{"detail": "用户名已被注册"}`
- 校验失败 (422): `{"detail": [{"loc": ["body", "username"], "msg": "ensure this value has at least 3 characters"}]}`

#### 3.2.2 登录

```
POST /api/auth/login
```

**请求体**：

```json
{
  "username": "zhangsan",
  "password": "mypassword123"
}
```

**成功响应 (200)**：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

`access_token` 即 JWT，后续请求在 Header 中携带。

**错误示例**：

- 用户名或密码错误 (401): `{"detail": "用户名或密码错误"}`

#### 3.2.3 获取当前用户信息

```
GET /api/auth/me
```

需要认证。

**响应示例 (200)**：

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "zhangsan",
    "created_at": "2026-07-10T12:00:00Z"
  },
  "message": "ok"
}
```

---

### 3.3 聊天（核心接口）

```
POST /api/chat
```

需要认证。这是整个系统最核心的接口——接收用户消息，返回 Agent 的流式响应。

**请求体**：

```json
{
  "message": "帮我规划一个杭州三日游，预算2000，喜欢自然风光",
  "trip_id": null
}
```

| 字段        | 类型     | 必填  | 说明                              |
| --------- | ------ | --- | ------------------------------- |
| `message` | string | 是   | 用户发送的消息文本                       |
| `trip_id` | string | 否   | 已有行程的 UUID。传入则表示继续已有对话；不传则创建新行程 |

**响应**：SSE (Server-Sent Events) 流式响应，Content-Type 为 `text/event-stream`。

#### SSE 事件类型

流式响应由多个 SSE 事件组成，每个事件格式为 `event: <事件名>\ndata: <JSON>\n\n`：

**事件 1: `token`** — 流式输出中的文本片段（多次发送）

```
event: token
data: {"content": "第一天：西湖..."}

event: token
data: {"content": "环湖漫步，苏堤春晓 → 断桥残雪..."}

event: token
data: {"content": "\n\n第二天：九溪十八涧 → 龙井村..."}
```

每个 `token` 事件携带 LLM 生成的一个文本片段。前端应将这些片段累积拼接，实现逐字渲染效果。

**事件 2: `plan`** — Agent 完成生成后，发送解析后的结构化行程数据

```
event: plan
data: {"trip_id": "xxx", "title": "杭州三日自然之旅", "plan_data": {...}}
```

`plan_data` 的结构见 2.2 节 PlanData 定义。

**事件 3: `done`** — 流结束

```
event: done
data: {}
```

**事件 4: `error`** — 发生错误

```
event: error
data: {"detail": "行程生成失败，请重试"}
```

#### 完整流式响应示例

```
event: token
data: {"content": "好的，我为您规划了一个杭州三日自然风光之旅。\n\n"}

event: token
data: {"content": "## 行程总览\n杭州三日游，预算 2000 元，以自然风光为主，兼顾人文体验。\n\n"}

event: token
data: {"content": "## 第一天：西湖经典..."}

... 更多 token 事件 ...

event: plan
data: {"trip_id":"550e8400-e29b-41d4-a716-446655440100","title":"杭州三日自然之旅","plan_data":{"destination":"杭州","duration":3,"budget":2000,"style":["自然风光"],"overview":"...","days":[...],"overall_tips":"..."}}

event: done
data: {}
```

#### 前端消费 SSE 示例

```typescript
async function sendMessage(message: string, tripId: string | null) {
  const response = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ message, trip_id: tripId }),
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // 按行解析 SSE
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';  // 保留不完整的最后一行

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        const eventType = line.slice(7).trim();
        // 下一行是 data: ...
        continue;
      }
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        switch (currentEvent) {
          case 'token':
            appendToDisplay(data.content);  // 追加文本到聊天区域
            break;
          case 'plan':
            updateTrip(data);  // 更新行程数据
            break;
          case 'done':
            finishStreaming();  // 结束流式显示
            break;
          case 'error':
            showError(data.detail);  // 显示错误
            break;
        }
      }
    }
  }
}
```

#### 错误响应（非流式，请求级别错误）

- 未认证 (401): `{"detail": "未提供有效的认证令牌"}`
- 校验失败 (422): `{"detail": [{"loc": ["body", "message"], "msg": "field required"}]}`
- LLM 超时 (504): 前端收到 `event: error` 事件

---

### 3.4 行程管理

#### 3.4.1 行程列表

```
GET /api/trips
```

需要认证。返回当前用户的所有行程，按更新时间倒序排列。

**查询参数**：

| 参数          | 类型      | 必填  | 默认值 | 说明         |
| ----------- | ------- | --- | --- | ---------- |
| `page`      | integer | 否   | 1   | 页码         |
| `page_size` | integer | 否   | 20  | 每页数量，最大 50 |

**响应示例 (200)**：

```json
{
  "data": {
    "trips": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440100",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "杭州三日自然之旅",
        "status": "confirmed",
        "created_at": "2026-07-10T12:00:00Z",
        "updated_at": "2026-07-10T12:05:00Z"
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440101",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "成都三日美食之旅",
        "status": "draft",
        "created_at": "2026-07-09T10:00:00Z",
        "updated_at": "2026-07-09T10:30:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "page_size": 20
  },
  "message": "ok"
}
```

> 列表不返回 `plan_data`（数据量大），详情需单独请求。

#### 3.4.2 行程详情

```
GET /api/trips/{trip_id}
```

需要认证。返回指定行程的完整信息，包含 `plan_data`。

**响应示例 (200)**：

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440100",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "杭州三日自然之旅",
    "plan_data": {
      "destination": "杭州",
      "duration": 3,
      "budget": 2000,
      "style": ["自然风光"],
      "overview": "三日行程...",
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
              "tips": "建议清晨前往，游客较少",
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
      "overall_tips": "杭州地铁覆盖主要景点..."
    },
    "status": "confirmed",
    "created_at": "2026-07-10T12:00:00Z",
    "updated_at": "2026-07-10T12:05:00Z"
  },
  "message": "ok"
}
```

**错误示例**：

- 行程不存在 (404): `{"detail": "行程不存在"}`
- 无权访问 (403): `{"detail": "无权访问此行程"}`
- 未经认证 (401): `{"detail": "未提供有效的认证令牌"}`

#### 3.4.3 删除行程

```
DELETE /api/trips/{trip_id}
```

需要认证。删除行程同时删除其关联的所有消息。

**响应示例 (200)**：

```json
{
  "data": null,
  "message": "行程已删除"
}
```

**错误示例**：同 3.4.2 详情接口。

---

## 4. 接口总览

| 方法     | 路径                     | 认证  | 说明             |
| ------ | ---------------------- | --- | -------------- |
| GET    | `/api/health`          | 否   | 健康检查           |
| POST   | `/api/auth/register`   | 否   | 用户注册           |
| POST   | `/api/auth/login`      | 否   | 用户登录           |
| GET    | `/api/auth/me`         | 是   | 当前用户信息         |
| POST   | `/api/chat`            | 是   | 发送消息（SSE 流式响应） |
| GET    | `/api/trips`           | 是   | 行程列表           |
| GET    | `/api/trips/{trip_id}` | 是   | 行程详情           |
| DELETE | `/api/trips/{trip_id}` | 是   | 删除行程           |

---

## 5. 错误处理最佳实践

**前端建议**：

- 401 错误：清除 localStorage 中的 Token，跳转登录页
- 422 错误：解析 Pydantic 校验详情，在表单字段旁显示错误提示
- SSE `error` 事件：在聊天区域显示错误提示，保留已生成的部分内容
- 网络超时：显示"网络连接失败，请检查后端是否正常运行"

**后端建议**：

- 所有异常经过统一的异常处理器，避免直接暴露 traceback
- 日志记录每次 LLM 调用的 Request ID 和耗时，方便排查
- SSE 连接中断时，后端应能清理资源（关闭 LLM 流、释放数据库连接）

---

> **文档元信息**
> 生成日期：2026-07-10
> 版本：v1.0
> 对应架构文档：旅游助手Agent架构设计.md
