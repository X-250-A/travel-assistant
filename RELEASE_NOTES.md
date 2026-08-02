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
```

---

## 升级注意事项

1. 后端需新增依赖 `redis[hiredis]`（uv.lock 已包含）
2. **必须启动 Redis**，否则 `init_redis()` 连不上直接 `sys.exit(1)` 退出
3. 新增配置项：`WEATHER_CACHE_TTL`、`RATE_LIMIT_REQUESTS`、`RATE_LIMIT_WINDOW`（均有默认值）
4. 无数据库迁移；`/logout` 为新增接口，前端 `logOut()` 已同步

---

## 下一步展望 (v0.6.0)

- [ ] Agent 记忆系统：偏好提取、跨会话持久化（Redis + 向量嵌入）
- [ ] 行程确认/编辑交互接后端
- [ ] ReAct 推理循环 + 反思机制
- [ ] 多 Agent 协作架构

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
