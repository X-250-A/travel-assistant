import { test, expect } from "@playwright/test";

/**
 * 完整用户旅程 E2E（v1.0.0）：
 * 注册（自动登录）→ 首页聊天生成行程（SSE 流式）→ 行程列表 → 行程详情。
 * 后端以 LLM_PROVIDER=mock 启动，其余链路全真。
 */
test("完整旅程：注册 → 聊天生成行程 → 列表 → 详情", async ({ page }) => {
    const username = `e2e_${Date.now()}`; // 随机用户名，多次运行不冲突
    const password = "Test123456";

    // ── ① 注册（注册成功自动登录并跳转首页） ──
    await page.goto("/register");
    await page.getByPlaceholder("请输入用户名").fill(username);
    await page.getByPlaceholder("请输入密码").fill(password);
    await page.getByRole("button", { name: "创建账号" }).click();

    // 注册接口 → 自动登录 → 跳转首页
    await expect(page).toHaveURL("/", { timeout: 20_000 });
    const token = await page.evaluate(() => localStorage.getItem("token"));
    expect(token).toBeTruthy();

    // ── ② 聊天生成行程（SSE 流式输出） ──
    const input = page.getByPlaceholder("说说你的旅行需求...");
    await expect(input).toBeVisible({ timeout: 15_000 });
    await input.fill("帮我规划 3 天成都游，预算 3000");
    await input.press("Enter");

    // 流式文本逐渐出现（mock LLM 返回固定行程 Markdown）
    await expect(page.getByText("已为您规划好成都 3 日游方案").first()).toBeVisible({
        timeout: 30_000,
    });
    // done 事件触发后 URL 携带 tripId
    await expect(page).toHaveURL(/\?tripId=\d+/, { timeout: 15_000 });

    // ── ③ 行程列表出现新行程 ──
    await page.goto("/trips");
    // 列表卡片渲染 plan_data.destination（📍 成都）
    await expect(page.getByText("📍 成都").first()).toBeVisible({ timeout: 15_000 });

    // ── ④ 详情页渲染每日安排 ──
    await page.getByText("📍 成都").first().click();
    await expect(page).toHaveURL(/\/trips\/\d+/);
    await expect(page.getByText("第 1 天")).toBeVisible({ timeout: 15_000 });
    // exact: true 避免匹配到"靠近武侯祠"这种餐厅建议
    await expect(page.getByText("武侯祠", { exact: true })).toBeVisible();
    await expect(page.getByText("宽窄巷子", { exact: true })).toBeVisible();
    // 详情页指标：目的地 + 天数 + 预算
    await expect(page.getByText("目的地:")).toBeVisible();
    await expect(page.getByText("3 天")).toBeVisible();
});
