from redis.asyncio import Redis
import time


async def check_rate_limit(r: Redis, key: str, limit: int, window: int) -> bool:
    """
    滑动窗口速率限制（Redis Sorted Set 实现）。

    原理：把每次请求的时间戳作为一个带分数的元素存进 Sorted Set，
    分数(score) 就是时间戳本身。每次请求时：
      1) 删掉"窗口之外"的旧时间戳
      2) 加入本次请求的时间戳
      3) 数一数窗口内还剩几个时间戳 = 窗口内请求数
    若超出 limit 则拒绝，否则放行。

    参数：
        r       : Redis 客户端（异步）
        key     : 限流对象的身份，如 "rate:login:1.2.3.4"。不同 IP/用户用不同 key，互不影响
        limit   : 窗口内允许的最大请求数
        window  : 滑动窗口长度（秒）
    返回：
        True  = 放行；False = 超限，拒绝
    """
    # 当前时间戳（浮点秒）。注意：这是"现在"，也是本请求的时间戳
    now = time.time()

    # 1. 删除窗口外的旧请求
    #    zremrangebyscore(key, min, max) 删除 score 在 [min, max] 区间的所有元素。
    #    这里删的是 score <= now-window 的旧时间戳 —— 它们已经超出滑动窗口，不再参与计数。
    #    ⚠️ 新手常把边界写成 limit（数量上限），那是错的：
    #       limit 是"最多允许几次"，now-window 才是"时间边界"。写错会一条都删不掉，
    #       导致 key 无限累加、第 limit+1 次之后永久拒绝，限流彻底失效。
    await r.zremrangebyscore(key, 0, now - window)

    # 2. 把本次请求的时间戳加进去（score 和 member 都用 now）
    #    这样每个元素既按时间排了序，又自带了时间信息，ZRANGEBYSCORE 就能按时间范围查。
    #    ⚠️ 小坑：若同一秒内有两个请求，now 相同，member 会被 Sorted Set 去重，只算一次。
    #       练手阶段可忽略；若要精确，可把 now 换成毫秒级时间戳或加随机后缀。
    await r.zadd(key, {now: now})

    # 3. 数一数窗口内现在有几个请求（元素个数 = score 在窗口内的时间戳数量）
    count = await r.zcard(key)

    # 4. 设置过期时间，防止 key 永久残留占内存
    #    窗口长 window 秒，窗口一旦滑过去这些元素自然失去意义，所以设 window 秒过期即可。
    await r.expire(key, window)

    # 判断是否超限。注意这是"加完本次请求后"再比较：
    # 前 limit 次时 count <= limit 放行，第 limit+1 次时 count == limit+1 > limit 被拒。
    return count <= limit

