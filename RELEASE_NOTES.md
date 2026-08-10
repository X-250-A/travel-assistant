# 发布记录

> 项目版本演进日志 · v0.1.0 → v0.8.0 · 最新版本在顶部

---

# Release v0.8.0 — "Critic 复盘" 🧐

> 2026-08-09 · 自 v0.7.0 起（1 次发布提交）

---

## 概述

v0.8.0 为 Agent 加上**自我批判（Critic）能力**：行程方案产出后，不再直接交给用户，而是先由第二轮 LLM 按「预算吻合 / 偏好遵守 / 可执行性」三个维度独立审查、结构化打分；不达标时带上审查反馈轻量重生成一版（上限可配，防无限循环）。这构成完整的**会思考 → 会自我纠错**故事链——Agent 从"能生成方案"升级为"能判断方案好坏并修正"。

---

## 后端 — Critic 复盘 🤖

### 1. 判定树（插入点）

Critic 插在 `handle_message` 的公共落库路径：`_extract_plan_json` 产出 `plan_data` 之后、`update_trip` 落库之前。因此**新建（_generate_plan）与修改（_apply_feedback）两条来源都自动覆盖**，无需改动任一生成函数。

### 2. 三个新方法

| 方法 | 职责 |
| --- | --- |
| `_ask_critic` | 发起第二轮 LLM 质量审查，仿 `llm_classify_intent` 用 `temperature=0` + `response_format=json_object`，返回 `{passed, scores, issues}`；失败降级返回 `None` |
| `_regenerate_plan` | 轻量单轮流式重生成（复用 `_apply_feedback` 范式：JSON dump 进 extra_system + 逐条 issues 修正指令），服务端累积不 yield 前端 |
| 判定树（handle_message 内） | 编排：审查 → 判定 → 条件重生成 → 落库 |

### 3. 审查维度

- **预算吻合（budget）**：budget 字段与用户预算是否一致，总花费是否控制在预算 80% 以内
- **偏好遵守（preferences）**：逐条对照 `conversation.pref`（如忌口辣 → 不推荐辣菜）
- **可执行性（feasibility）**：景点就近顺序、单日时长、交通衔接、餐饮位置

审查器 system prompt 独立为 `critic-prompt.txt`（不复用 trip-agent 人设——审查员是另一个角色）。

### 4. 判定树规则

```
拿到 verdict：
├─ None（审查失败/超时/解析失败）→ 用原方案（降级不阻断主流程）
├─ passed=True → 用原方案
├─ passed=False 但 issues 为空 → 用原方案（无可执行修正项）
└─ passed=False 且 issues 非空 → 重生成（循环最多 CRITIC_MAX_REGENERATE 次，
    产出合法 JSON 即采纳；全失败则保持原方案）
```

### 5. 事件流

```
token(逐字)   … v1 完整文本（打字机）…
thinking      我现在要使用 get_weather, budget_calculate 工具…（ReAct 阶段，原有）
token(逐字)   … v1 剩余文本（含 ```json 块）…
thinking      正在对行程方案做质量审查…
thinking      审查发现部分安排需要优化，正在重新生成方案   ← 仅重生成时
done          {"trip_id": ...}
```

v2 重生成文本**不 yield 成 token**（否则前端气泡会拼 v1+v2 含两个 JSON 块），只服务端累积、落库 v2，用 thinking 气泡提示用户。**零前端改动**。

---

## 修复 🐛

| 问题 | 修复 |
| --- | --- |
| `_ask_critic` 的 try/except 只包住解析、没包住 `create` 调用 | LLM 调用抛异常时降级路径失效，改为调用+解析整体 try 包裹 |
| 判定树未读 `CRITIC_ENABLED` 开关 | 开关定义了但没生效，条件补上 `settings.CRITIC_ENABLED` |

---

## 配置 ⚙️

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `CRITIC_ENABLED` | `True` | 总开关：对新建/修改的行程方案做第二轮质量审查 |
| `CRITIC_MAX_REGENERATE` | `1` | 审查不达标时的最大重生成次数（防无限循环烧 token） |

测试环境通过 conftest 设 `CRITIC_ENABLED=false` 关闭，现有测试零改动。

---

## 测试 ⚙️

- **68 passed / 3 skipped** —— v0.7.0 基线（59）新增 9 个 Critic 用例，零回归
- 新增 `test_critic.py` 覆盖判定树全分支：
  - 审查通过 → 落库原方案、chat_stream 仅 1 次
  - 审查不达标 → 重生成一次、落库 v2、chat_stream 恰好 2 次
  - 重生成无合法 JSON → 落库 v1（防无限循环）
  - 审查 LLM 抛异常 / 返回非 JSON → 降级原方案、流程不崩
  - `CRITIC_ENABLED=false` / `plan_data=None` → 审查永不调用
  - modify_trip 修改方案也走审查
  - 审查 messages 构造（含 critic 人设 + 需求 + 偏好 + 行程 JSON）
- **实机验证**（真实 DeepSeek + 真实 Redis）：
  - 超预算 + 含辣菜行程 → `passed=false`，`preferences: 0`，issues 准确指出「大龙燚火锅特辣锅底违反忌口辣」+「缺第2/3天」
  - 预算内 + 不辣 + 3 天完整行程 → `passed=true`，三维度全 100，`issues: []`
  - 审查器能区分好方案与差方案，且给出可执行修正方向

---

## 完整 Changelog

```
4649d88 feat: v0.8.0 行程方案 Critic 复盘（自评自纠）   ← 当前
ed94614 docs: v0.8.0 版本文档升级 — RELEASE_NOTES 记录 Critic 复盘发布
```

---

## 升级注意事项

1. 新增配置项 `CRITIC_ENABLED`（默认 True）、`CRITIC_MAX_REGENERATE`（默认 1），无需手动配置
2. 生产默认开启审查，每次行程多一次 LLM 调用（约 2-10s）；可设 `CRITIC_ENABLED=false` 一键关闭
3. 无数据库迁移；`critic-prompt.txt` 为新增模板文件，随代码部署
4. 测试默认关审查（conftest 设 `CRITIC_ENABLED=false`），不影响既有 59 用例

---

## 下一步展望 (v0.9.0)

- [ ] 记忆升级：向量语义检索 + 景点查询工具（v0.9.0）
- [ ] 测试覆盖、E2E、Docker 生产部署（v1.0.0）

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---
# Release v0.7.0 — "ReAct 觉醒" 🤖

> 2026-08-07 · 自 v0.6.0 起（1 次发布提交）

---

## 概述

v0.7.0 为 Agent 装上了真正的 **ReAct 推理循环**：模型不再"一轮工具调用后直接输出"，而是进入 **Thought（思考）→ Action（行动）→ Observation（观察）** 的闭环，基于工具结果自我评估、自我纠错，直到信息充分才组织最终行程。这标志着 Agent 从"会调用工具"升级为"会思考为什么调用工具"。

---

## 后端 — ReAct 推理循环 🤖

### 1. 循环结构

`_generate_plan` 的工具调用分支升级为完整的 ReAct 回路：

- **Thought**：工具结果回填后，注入 `[内部推理]` 反思消息——模型基于已掌握的全部信息评估"是否满足用户需求"，决定停止还是补调
- **Action**：保留 OpenAI function-calling 原生工具调用（`tool_calls`）
- **Observation**：每轮执行工具后，结果回填 `messages`（`role: tool`），并汇总进 `thoughts` 轨迹（保留最近 3 轮，截断长结果控 token）
- **收敛指令**：反思消息显式引导"若已满足，直接回答，不要调用工具"，避免无限兜底

### 2. 事件分流

`handle_message` 消费流式生成器时按事件类型分流：`token` 事件拼进消息文本并转发前端打字机；`thinking` 事件原样透传、**不进入消息文本**。

### 3. 前端配套

SSE 链路新增 `thinking` 事件：`api.ts` 解析 → `useChat` 维护 `thinking` 状态 → `ChatContainer` 渲染"🤔 Agent 正在思考"气泡。

---

## 修复 🐛

| 问题 | 修复 |
| --- | --- |
| 工具轮次 `assistant.content=None` 被流式输出污染回复 | 工具轮只回填 messages、不 yield 文本，最终轮才流式输出 |
| `tool_calls` 回填重复导致 API 400 | 删除冗余的 `else` 分支回填，只保留循环内统一回填点 |
| 工具轮 `yield` 裸字符串与事件结构不一致 | `_generate_plan` 全部事件统一为 `{"type": ..., "content": ...}` 结构 |

---

## 测试 ⚙️

- **59 passed / 3 skipped** — 与 v0.6.0 基线一致，零回归
- ReAct 实机验证（真实 DeepSeek + 真实天气/预算/交通工具 + 真实 Redis）：
  - 模型第一轮并行调用 5 个工具 → 反思发现舒适档 ¥3600 超预算 → 第二轮**针对性补调经济档重算** → 收敛输出行程 JSON
  - `[内部推理]` 在第 2、3 次 LLM 调用时均成功注入
  - 最终行程 JSON 可解析（成都 / 3 天 / 预算内）

---

## 完整 Changelog

```
385c46d feat: v0.7.0 ReAct 推理循环（Thought-Action-Observation）+ 反思机制   ← 当前
```

---

## 升级注意事项

1. 后端 `_generate_plan` 事件结构统一为 `{type, content}`，前端 SSE 解析已同步支持 `thinking` 事件
2. Redis 仍是硬依赖：`init_redis()` 连不上直接 `sys.exit(1)`
3. 无数据库迁移；无新增配置项

---

## 下一步展望 (v0.8.0)

- [ ] 多 Agent 协作架构（Orchestrator + Research/Planner/Reviewer）
- [ ] 记忆升级：向量语义检索 + 景点查询工具（v0.9.0）

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

# Release v0.6.0 — "记忆觉醒" 🧠

> 2026-08-04 · 自 v0.5.0 起（1 次发布提交）

---

## 概述

v0.6.0 为 Agent 装上 **长期记忆**：从对话中自动提取用户偏好（饮食忌口、预算上限、出行限制、节奏），跨会话持久化到 Redis，并在每次规划时注入 System Prompt 严格遵守。同时补齐行程交互闭环：标题行内编辑 + 行程确认。这是从"每次对话从零开始"迈向"越聊越懂你"的关键一步。

---

## 后端 — Agent 记忆系统 🧠

### 1. 偏好提取与跨会话持久化

新增 `memory/preferences.py` — 规则而非向量嵌入：

| 类型  | 正则示例                  | 合并策略            |
| --- | --------------------- | --------------- |
| 饮食  | `"不吃辣"` → 忌口辣         | **累加**（可积累多条忌口） |
| 预算  | `"预算3000元"` → 上限3000元 | 覆盖              |
| 出行  | `"不想爬山"`              | 覆盖              |
| 节奏  | `"不要赶行程"`             | 覆盖              |

- 存储：Redis Hash `user:preferences:{user_id}`，TTL = `PERMANENT_SESSION_LIFETIME`（30 天）
- 注入：`PromptBuilder.render_preferences()` 将偏好拼为 System Prompt 附加段"用户偏好（必须严格遵守，违反即为错误）"
- 设计决策：**偏好是低熵结构化信息，正则精确、零成本、可解释**；向量语义检索留待 v0.9.0

### 2. 行程交互闭环

- 行程确认：`draft → confirmed`（此前 v0.5.0 已接通）
- 行程标题行内编辑：前端 `EditableTitle` 组件调 PATCH 更新，即时回显

---

## 修复 🐛

| 问题                                   | 修复                                            |
| ------------------------------------ | --------------------------------------------- |
| `create_trip` 收到会话状态 `idle/planning` | 改为固定写合法值 `"draft"`（Trip 与 Conversation 是两套枚举） |
| CORS 预检 `OPTIONS` 请求被 JWT 拦截 401     | 中间件放行 OPTIONS，预检不参与鉴权                         |
| chat 路由 Redis 连接泄漏                   | `get_redis(0)` → `finally: r.aclose()` 保证随响应关闭 |
| 新配置项                                 | `PERMANENT_SESSION_LIFETIME`（偏好 TTL，默认 30 天）  |

---

## 测试 ⚙️

- **59 passed / 3 skipped** — 与 v0.5.0 基线一致，零回归
- `conftest.py` 的 `mock_redis` 扩展到 **5 个 patch 点**（含 `chat`）+ 偏好方法（`hgetall` / `hmset`）
- `test_planner.py` 适配 `handle_message` 新增 Redis 参数

---

## 完整 Changelog

```
3733b21 docs: v0.6.0 版本文档升级 — RELEASE_NOTES + 架构/API 文档版本引用
3064145 feat: v0.6.0 Agent 记忆系统（偏好提取 + Redis 持久化 + Prompt 注入）   ← 当前
```

---

## 升级注意事项

1. 新增配置项 `PERMANENT_SESSION_LIFETIME`（默认 `2592000` = 30 天），无需手动配置
2. Redis 仍是硬依赖：`init_redis()` 连不上直接 `sys.exit(1)`
3. 无数据库迁移；记忆 key 自动随首次对话创建
4. 前端 `TripDetail` 新增可选 `onTitleChange` 回调，未传时退化为只读标题

---

## 下一步展望 (v0.7.0)

- [ ] ReAct 推理循环 + 反思机制（Thought-Action-Observation）
- [ ] 多 Agent 协作架构（Orchestrator + Research/Planner/Reviewer）
- [ ] 记忆升级：向量语义检索 + 景点查询工具（v0.9.0）

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

# Release v0.5.0 — "Redis 上云" 🚀

> 2026-08-02 · 累计 2 commits 自 v0.4.0

---

## 概述

v0.5.0 完成 **Redis 基础设施** 三件套：JWT Token 黑名单主动吊销、滑动窗口速率限制、天气查询缓存。安全与性能双升级，并配套前端登出真正调用后端接口。这是从"纯本地 SQLite 单机应用"迈向"带中间件与缓存的正式服务"的关键一步。

---

## 后端 — Redis 基础设施 🛡️

### 1. Token 黑名单（主动吊销）

JWT 签发时携带 `jti` / `iat` 字段；`POST /api/auth/logout` 将 `jti` 写入 Redis 黑名单（独立 DB 1），JWT 中间件每请求校验黑名单，登出即失效。

| 组件 | 说明 |
|---|---|
| `db/redis.py` | Redis 连接池封装，`get_redis(db)` 支持多 DB |
| `middleware/auth_middleware.py` | 黑名单校验，命中返回 **403**（修正自 401） |
| `routers/auth.py` | 新增 `/logout` 接口，`jti` 加入黑名单并设过期 |

### 2. 滑动窗口速率限制

新增 `ratelimit/core.py` — 基于 **Redis Sorted Set** 的滑动窗口限流：

```
每次请求：
  ① ZREMRANGEBYSCORE 删除窗口外的旧时间戳
  ② ZADD 加入本次请求时间戳
  ③ ZCARD 统计窗口内请求数
  ④ 超出 limit → 429 拒绝；未超出 → 放行
```

- `ip_ratelimit` 依赖已接入 **register / login** 两接口，防批量注册与爆破登录
- 限流 key 按 `IP + 路径` 隔离，各接口互不影响
- 配置项：`RATE_LIMIT_REQUESTS`（默认 30 次/分）、`RATE_LIMIT_WINDOW`（默认 60 秒）

### 3. 天气查询缓存

`tools/weather.py` 接入 Redis 缓存：

- key 归一化（日期缺省时取今天），提高命中率
- TTL = `WEATHER_CACHE_TTL`（1 小时）+ ±300s 随机抖动，**防雪崩**
- 相同城市+日期的二次查询直接命中缓存，零外部 API 调用

### 4. 其他

- `REDIS_URL` 默认值指向虚拟机 `192.168.126.128:6379`
- 黑名单响应码 401 → 403（语义更准确：token 本身有效，但已被吊销）

---

## 前端 — 登出真实化 🖥️

| 文件 | 变更 |
|---|---|
| `lib/api.ts` | `logOut()` 从"仅清 localStorage"改为真实调用 `POST /api/auth/logout` |
| `hooks/useAuth.tsx` | `logout` 变为 async；`finally` 保证无论接口成败都清理本地 token |

登出流程升级：**前端清 token + 后端黑名单吊销** 双保险，旧 token 即使泄露也无法再使用。

---

## 测试 ⚙️

- **59 passed / 3 skipped** — 与 v0.4.0 基线一致，零回归
- `conftest.py` 的 `mock_redis` 补齐新使用点（`dependencies`、`weather`）+ Sorted Set / 缓存方法
- ⚠️ 运行需要真实 Redis：开发地址 `redis://192.168.126.128:6379/0`（虚拟机 Docker），测试环境自动 mock

---

## 完整 Changelog

```
027cb67 feat: v0.5.0 Redis 速率限制（滑动窗口）+ 天气缓存 + 前端登出接后端   ← 当前
cf5d7c2 feat: Redis 集成（Token 黑名单 + 登出接口）+ 修复测试环境
267295a docs: v0.5.0 版本文档升级 — RELEASE_NOTES + 架构/API 文档版本引用
```

---

## 升级注意事项

1. 后端需新增依赖 `redis[hiredis]`（uv.lock 已包含）
2. **必须启动 Redis**，否则 `init_redis()` 连不上直接 `sys.exit(1)` 退出
3. 新增配置项：`WEATHER_CACHE_TTL`、`RATE_LIMIT_REQUESTS`、`RATE_LIMIT_WINDOW`（均有默认值）
4. 无数据库迁移；`/logout` 为新增接口，前端 `logOut()` 已同步

---

## 下一步展望 (v0.6.0)

- [x] Agent 记忆系统：偏好提取、跨会话持久化（Redis Hash + 规则提取）
- [x] 行程确认/编辑交互接后端
- [ ] ReAct 推理循环 + 反思机制（v0.7.0）
- [ ] 多 Agent 协作架构（v0.8.0）

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

# Release v0.4.0 — "视觉重生" 🎨

> 2026-07-29 · 累计 6 commits 自 v0.3.0

---

## 概述

v0.4.0 是一次**视觉与架构双重重构**。前端全面焕新设计语言，摆脱组件库默认风格；后端工具系统从硬编码字典升级为可插拔的注册中心，并新增预算计算工具。

---

## 前端 UI — 设计系统全面升级 ✨

### 设计令牌 (Design Tokens)

彻底告别蓝/灰体系，建立暖色调旅行品牌色：

| 令牌 | 色值 | 用途 |
|------|------|------|
| `--color-primary` | `#f97316` (Orange 500) | 主操作按钮、强调色 |
| `--color-accent` | `#0ea5e9` (Sky 500) | 辅助强调、链接 |
| `--color-surface` | `#fafaf9` (Stone 50) | 卡片底色 |
| `--color-text` | `#1c1917` (Stone 900) | 正文 |

- 字体切换为 **Noto Sans SC + Noto Serif SC**（Google Fonts），替换 Geist
- 全局背景改为**暖色渐变**：奶油色 → 桃子色 → 粉紫色 → 天空蓝
- 移除 dark mode，专注浅色体验
- 新增 4 个 CSS 关键帧动画：`fadeInUp`、`fadeIn`、`slideInLeft`、`slideInRight`、`scaleIn`

### UI 组件升级

**Button** — 新增 `ghost`、`accent` 变体；主按钮改为渐变圆角（`orange→rose`），带阴影 + 点击缩放反馈；loading 状态带 SVG spinner

**Card** — 新增 `variant` 属性（`default` / `glass` / `flat`），`padding` 可控（`sm` / `md` / `lg`），圆角从 `rounded-lg` 升级为 `rounded-2xl`

**Loading** — 双层圆环旋转动画（外层浅色轨道 + 内层彩色旋转），支持自定义 `text`

### 页面/组件视觉重写

- **ChatContainer**: 消息列表宽度约束 `max-w-4xl`，新增空状态引导页
- **TripDetail**: 状态标签（✅已确认 / 📝草稿），旅程指标行（目的地/天数/预算），glass 风格卡片
- **TripCard**: 悬停阴影、新配色标签
- **AuthForm**: 配色与按钮风格统一
- **ChatInput / MessageBubble / StreamingText**: 细节打磨

**影响范围**: 18 个前端文件，+1003 行 / -587 行

---

## 后端 — 工具系统重构 🔧

### 工具注册中心

新增 `backend/app/tools/base.py` — `Tool` dataclass 统一工具定义：

```python
@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    required: list[str]
    handler: Callable[..., Awaitable[str]] | None
```

新增 `backend/app/tools/__init__.py` — 工具注册与调度：

```python
ALL_TOOLS: list = [weather_tool, budget_calculate_tool]

def get_tool_schema()     # → 生成 OpenAI function-calling 格式
async def execute_tool()  # → 按 name 分发执行
```

### 天气工具重构

`weather.py` 从硬编码字典改为 `Tool` dataclass 注册，定义与实现分离。

### 新工具：预算计算

`budget_calculate.py` — 根据**天数 / 人数 / 档次**（经济/舒适/豪华）估算旅行预算，输出住宿、餐饮、交通、门票分项明细。支持 tool calling 自动调用。

### LLM Agent 适配

`planner.py` 适配新的 `get_tool_schema()` + `execute_tool()` 接口。

**影响范围**: 5 个后端文件（4 修改 + 1 新增），+67 行 / -31 行

---

## 完整 Changelog

```
b355205 feat: 前端 UI 全面优化 + 后端工具注册机制重构 + 新增预算计算工具  ← 当前
5672dd9 feat: LLM意图分类 + gossip闲聊分流 + 工具调用循环防护
83ad0cb chore: 将日记目录加入.gitignore
a59f2dd feat: 添加tool calling机制与天气预报工具
f2adbd6 fix: 修复AI重复发言与纯JSON输出问题
7902f04 修正.env.exmaple和README文件
```

---

## 升级注意事项

1. 前端需重新 `npm install` 获取 Tailwind v4 依赖
2. 后端需确认 `backend/app/tools/` 目录存在（新增 `__init__.py`、`base.py`、`budget_calculate.py`）
3. 无数据库迁移，无 API breaking changes

---

## 下一步展望 (v0.5.0)

- [x] 前端：行程确认/编辑交互
- [x] 后端：middleware 鉴权中间件实现
- [x] 工具：景点查询、交通规划等新工具
- [ ] 测试：提高覆盖率，补充 E2E 测试（v1.0.0）

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

# Release v0.3.0 — 意图分类与闲聊分流

> 2026-07-28 · Git 有 tag，未单独发布 GitHub Release（功能并入 v0.4.0 展示）

---

## 概述

v0.3.0 为 Agent 引入 **LLM 意图分类** 与 **闲聊分流**，并补上**工具调用循环防护**——Agent 不再只会一股脑地规划，而是能判断用户到底想新建行程、修改行程还是单纯聊天。

---

## 核心能力

- **LLM 意图分类**：`response_format: json_object` + temperature=0 精确分类
  - `new_trip` / `modify_trip` / `ask_question` 三通道分流
  - LLM 调用失败时降级到**关键词匹配 fallback**，保证服务可用
- **闲聊分流（gossip）**：不涉及行程的对话走自由闲聊，不误触发规划流程
- **工具调用循环防护**：最多 10 轮工具调用硬上限，防止模型陷入死循环消耗 token

---

## 完整 Changelog

```
5672dd9 feat: LLM意图分类 + gossip闲聊分流 + 工具调用循环防护  ← 当前
83ad0cb chore: 将日记目录加入.gitignore
a59f2dd feat: 添加tool calling机制与天气预报工具
f2adbd6 fix: 修复AI重复发言与纯JSON输出问题
7902f04 修正.env.exmaple和README文件
```

---

> 注：v0.3.0 在 Git 中有 tag（`5672dd9`），但未发布 GitHub Release；其功能在 v0.4.0 的 Release 中已包含。

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

# Release v0.2.0 — "Tool Calling 降临" 🛠️

> 2026-07-28 · 基于 MVP（v0.1.0）以来的第一个功能版本

---

## 新功能 ✨

### Tool Calling 机制

Agent 不再只会"说"，现在能"做"了。LLM 可以自主判断何时需要调用外部工具，并在对话中返回工具执行结果。

- 新增工具基类 `backend/app/tools/base.py`
- Planner 重构，支持 tool call 的解析、执行与结果回传
- 新增 tool calling 单元测试 `backend/tests/test_tool_use.py`

### 天气预报工具 🌤️

首个接入的实际工具。Agent 可以查询指定城市的天气信息，让旅行规划更实用。

- 新增 `backend/app/tools/weather.py`
- LLM 系统提示词同步更新，教会模型何时调用天气工具

---

## Bug 修复 🐛

- **AI 重复发言**：修复同一轮对话中 AI 多次输出相同回复的问题，现在每次回复都是新鲜的
- **纯 JSON 输出**：修复对话输出直接裸 JSON（而不是自然语言）的问题，用户看到的是可读文本

---

## 文档 & 杂项 📝

- 修正 `.env.example` 和 README.md 中的配置说明
- 将日记目录加入 `.gitignore`

---

# Release v0.1.0 — "项目 MVP" 🎉

> 2026-07-28 · 首次公开发布

---

## 概述

旅游规划 Agent 助手的首次公开发布。一个"能用"的起点——前后端分离，AI 对话驱动旅行规划，从零到完整骨架一气呵成。

---

## 项目架构 🏗️

```
前端 (Next.js 15)  ←→  REST API  ←→  后端 (FastAPI)  ←→  LLM (Claude / DeepSeek)
         ↕                                   ↕
    PostgreSQL  ←→  SQLAlchemy ORM  ←→  Docker Compose 一键部署
```

---

## 核心功能 ✨

### 🤖 AI 旅行规划对话

- 与 AI Agent 自然语言对话，规划你的旅行
- 支持流式输出（SSE），AI 回复逐字呈现，体验流畅
- Agent 理解旅行场景：目的地、天数、预算、偏好

### 👤 用户认证

- 注册 / 登录系统
- JWT Token 鉴权，保护用户数据
- 密码安全哈希存储

### 📋 旅行管理

- 创建、查看、编辑、删除旅行计划
- 每个旅行关联独立的对话记录
- 对话历史持久化保存

### 🧱 技术基础设施

- Docker Compose 一键启动后端 + 数据库
- 完整的单元测试覆盖（Auth、Chat、Planner、LLM）
- 前后端分离架构，RESTful API 设计
- PostgreSQL 数据持久化

---

## 技术栈 📦

| 层 | 技术 |
|---|---|
| **前端** | Next.js 15, React 19, TypeScript |
| **后端** | Python 3.12, FastAPI, SQLAlchemy, Pydantic |
| **数据库** | PostgreSQL 16 |
| **AI** | Claude API / DeepSeek API |
| **部署** | Docker Compose, 一键启动脚本 |
| **测试** | pytest + httpx |

---

## 项目规模 📊

105 files changed, 12,832 insertions(+)

---

## 快速开始 🚀

```bash
cp .env.example .env
docker compose up -d
```

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
