from redis.asyncio import Redis, ConnectionPool
from backend.app.config import settings
import sys
from redis.asyncio import ConnectionError as RedisConnectionError


_pool: ConnectionPool | None = None

async def init_redis() -> None:
    global _pool
    try:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
        )
        async with Redis(connection_pool=_pool) as r:
            await r.ping()
    except RedisConnectionError:
        print(f"[Redis] 无法连接到 {settings.REDIS_URL}")
        print("[Redis] 请确认：")
        print("[Redis]   1. Redis 服务是否已启动")
        print("[Redis]   2. 地址和端口是否正确")
        print("[Redis]   3. 如果使用 Docker: docker run -d --name redis -p 6379:6379 redis:7-alpine")
        sys.exit(1)  # 直接退出，不让应用在无 Redis 的状态下运行
    print(f"[Redis] 连接池已建立: {settings.REDIS_URL}")

async def close_redis() -> None:
    """应用关闭时调用，释放连接池中所有连接"""
    global _pool
    if _pool is None:
        return
    await _pool.disconnect()
    _pool = None
    print("[Redis] 连接池已释放")


async def get_redis(db: int = 0) -> Redis:
    """从连接池获取一个 Redis 客户端，操作指定 DB"""
    if _pool is None:
        raise RuntimeError("Redis 连接池未初始化，请先调用 init_redis()")

    r = Redis(connection_pool=_pool)
    if db != 0:
        await r.execute_command("SELECT", db)
    return r