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

- [ ] 前端：行程确认/编辑交互
- [ ] 后端：middleware 鉴权中间件实现
- [ ] 工具：景点查询、交通规划等新工具
- [ ] 测试：提高覆盖率，补充 E2E 测试

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
