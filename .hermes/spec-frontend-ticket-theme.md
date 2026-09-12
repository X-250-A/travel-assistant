# 任务：旅游助手前端「车票主题」全面统一（首页以外页面）

你在一个 Next.js 15 (App Router) + Tailwind v4 项目里工作。工作目录：
D:\agent个人项目开发\从零开始型\travel-asistant-of-Mr-An\frontend

你已安装 frontend-design skill，先读取它并按其方法论执行。

## 背景与目标

首页 LandingPage（app/page.tsx 的 LandingPage 函数 + 文件底部的设计令牌）已按"车票主题"重设计并获用户认可：
- 令牌：PAPER #F7F3EA（页面底）、INK #16324F（墨蓝标题）、ORANGE #E56A1F（检票橙 CTA）、MIST #7A9AA8（烟青次要文字）、CHAR #26221C（炭墨细节）、TICKET_FACE #FFFDF7（票面米白）、STAMP_RED #C8442A（邮戳红）
- 字体：Noto Serif SC 衬线做 display 标题，ui-monospace 做眉标/编号
- 签名元素：车票隐喻（票面卡片、撕票线、邮戳、检票口语汇）

其余页面还是旧风格（stone 灰系 + glass 卡片 + emoji 图标 + 橙紫渐变），与首页割裂。
**你的任务：把登录、注册、行程列表、行程详情四个页面统一到车票主题，形成完整连贯的视觉体系。**

## 涉及文件（全部在 frontend/ 下）

1. app/login/page.tsx（登录页，62 行）
2. app/register/page.tsx（注册页，60 行）
3. components/auth/AuthForm.tsx（登录/注册共用表单：输入框、错误提示、按钮）
4. app/trips/page.tsx（行程列表页，102 行）
5. components/trip/TripCard.tsx（行程卡片，124 行）
6. app/trips/[id]/page.tsx（行程详情页壳，135 行）
7. components/trip/TripDetail.tsx（行程详情主体：概览卡、逐日行程，262 行）
8. components/trip/EditableTitle.tsx（如需跟随新风格可微调）
9. components/ui/Button.tsx、Card.tsx、Loading.tsx（被全站共用——只调整配色/圆角/阴影令牌使其服务车票主题，不破坏已有调用方）

## 设计要求（按 frontend-design skill 执行，以下是硬约束）

1. **令牌单一来源**：把车票主题令牌（PAPER/INK/ORANGE/MIST/CHAR/TICKET_FACE/STAMP_RED + serif/mono 字体）提升到 app/globals.css 的 :root 和 @theme inline（替换/融合现有 orange/sky/stone 令牌），页面里用 Tailwind 类或 CSS 变量引用，不再各文件硬编码十六进制。现有 globals.css 的动画 keyframes 保留。
2. **登录/注册**：做成"检票口"隐喻——页面像车站检票口，表单卡片是一张待检的车票（票面米白、撕票虚线、检票孔），按钮文案可用「检票进站」（登录）「签发车票」（注册）这类语汇。错误提示用邮戳红。保留全部现有逻辑（useAuth、路由跳转、Suspense），只动视觉层。
3. **行程列表**：页头用 mono 眉标（如 MY TICKETS / 车票夹），每张 TripCard 是一张真实车票：目的地为站名、日期为乘车日期、status 映射为"已检票/待检票"（confirmed=已检票 用邮戳红斜章效果或对勾章）。卡片可做撕票线（虚线打孔）细节。空状态 = 空票夹插画感，不是居中 emoji。
4. **行程详情**：概览卡 = 票面（车票头图区：起讫站 + 大字目的地衬线字），逐日行程 DayPlan 用"站台编号"式 mono 编号（DAY 01），风格标签改为检票员批注风格。Metric 指标行对齐票面排版。
5. **克制**：全局只允许一个 signature 级元素（车票卡片本身），emoji 图标（🗺️✈️📍💰等）全部去掉或替换为 mono 短标签（如 DEP/ARR/CLASS），不要堆动画。页面进场动画沿用现有 keyframes，prefers-reduced-motion 必须降级。
6. **质量底线**：移动端 375px 可用；键盘 focus 可见（focus-visible ring 用检票橙）；不改任何业务逻辑/API 调用/状态管理；TypeScript 类型不破坏（`npx tsc --noEmit` 通过）。
7. ChatContainer / ChatInput / MessageBubble 本次**不动**（后续批次），但 Button/Card/Loading 是共用的，改动不能让聊天区样式爆炸——改动后跑 `npm run build` 验证全站编译通过。

## 自查与验证（必做，最多重试 2 次后交盘）

1. `npm run build` 通过（在 frontend/ 下）
2. `npx tsc --noEmit` 无新错误
3. 启动 dev server（`npm run dev`，端口 3300 避免冲突）后用 curl 确认 /login /register /trips 返回 200 即可（无浏览器截图能力，不用做视觉自检）
4. 输出改动文件清单 + 每个文件改了什么的一句话说明

## 边界

- 只改 frontend/ 目录，不碰 backend/
- 不改 app/page.tsx 的 LandingPage（那是已完成基准），但 app/page.tsx 中登录后区域的 header（你会在 40-108 行看到旧风格导航）允许同步统一成车票主题——它和列表页共用视觉
- 不新增依赖包
- 不要 git commit，改完即止
