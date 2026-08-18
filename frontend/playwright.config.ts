import { defineConfig, devices } from "@playwright/test";

/**
 * E2E 配置：webServer 自动拉起后端（mock LLM 模式）+ 前端。
 * 前置条件：本机 6379 端口有一个 Redis 服务（E2E 用 DB 15，隔离开发数据）。
 */
export default defineConfig({
    testDir: "./e2e",
    timeout: 90_000,
    workers: 1, // 串行：用例共享后端数据（注册/登录/行程状态）
    retries: process.env.CI ? 2 : 1,
    reporter: [["list"], ["html", { open: "never" }]],
    use: {
        baseURL: "http://localhost:3000",
        trace: "retain-on-failure", // 失败自动录 trace，npx playwright show-trace 回放
        screenshot: "only-on-failure",
    },
    webServer: [
        {
            // 后端：mock LLM + 独立测试库 + Redis DB 15（隔离开发数据）
            command: "uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000",
            url: "http://127.0.0.1:8000/docs",
            reuseExistingServer: !process.env.CI,
            timeout: 120_000,
            cwd: "../", // 项目根（pyproject.toml 所在）
            env: {
                LLM_PROVIDER: "mock", // ★ 唯一 mock：LLM 回复
                SECRET_KEY: "e2e-test-secret-key",
                DATABASE_URL: "sqlite+aiosqlite:///./e2e_test.db",
                REDIS_URL: "redis://127.0.0.1:6379/15?protocol=2", // protocol=2 兼容 Redis 5（HELLO 3 是 Redis 6+）
                SILICONFLOW_API_KEY: "change-me", // 禁用真实 embedding（走降级）
                DEEPSEEK_API_KEY: "test-deepseek-key",
                DEEPSEEK_BASE_URL: "https://test-deepseek.example.com/v1",
            },
        },
        {
            // 前端：--webpack 绕过 Turbopack（Windows 沙箱下 EPERM）
            command: "npx next dev --webpack",
            url: "http://localhost:3000",
            reuseExistingServer: !process.env.CI,
            timeout: 120_000,
        },
    ],
    projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
