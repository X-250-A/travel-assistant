"""认证模块测试 — POST /api/auth/register | /login | GET /api/auth/me"""

from httpx import AsyncClient

from backend.tests.conftest import TEST_USERNAME, TEST_USERNAME_ALT, _login, _register


class TestRegister:
    """POST /api/auth/register"""

    async def test_register_success(self, async_client: AsyncClient):
        resp = await _register(async_client, "newuser", "mypassword123")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["id"] > 0

    async def test_register_duplicate_username(self, async_client: AsyncClient):
        await _register(async_client, "dupuser", "abc123")
        resp = await _register(async_client, "dupuser", "xyz456")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "用户名已存在"


class TestLogin:
    """POST /api/auth/login"""

    async def test_login_success(self, async_client: AsyncClient):
        await _register(async_client, "logintest", "correctpass")
        resp = await _login(async_client, "logintest", "correctpass")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, async_client: AsyncClient):
        await _register(async_client, "badpwuser", "right")
        resp = await _login(async_client, "badpwuser", "wrong")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "用户名或密码错误"

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        resp = await _login(async_client, "nobody", "whatever")
        assert resp.status_code == 401


class TestMe:
    """GET /api/auth/me"""

    async def test_me_with_valid_token(self, async_client: AsyncClient, auth_headers: str):
        resp = await async_client.get("/api/auth/me", headers={"Authorization": auth_headers})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["username"] == TEST_USERNAME
        assert data["id"] > 0

    async def test_me_without_token(self, async_client: AsyncClient):
        resp = await async_client.get("/api/auth/me")
        # 中间件优先于路由依赖拦截，缺 Authorization → 401（而非依赖层的 422）
        assert resp.status_code == 401

    async def test_me_with_invalid_token(self, async_client: AsyncClient):
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer this-is-not-valid-jwt"},
        )
        assert resp.status_code == 401

    async def test_me_with_second_user(self, async_client: AsyncClient, auth_headers_alt: str):
        """确保 /me 返回的是第二个用户，而非第一个"""
        resp = await async_client.get("/api/auth/me", headers={"Authorization": auth_headers_alt})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["username"] == TEST_USERNAME_ALT
