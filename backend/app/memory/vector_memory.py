import math
import json
from redis.asyncio import Redis

# 手写的余弦相似度计算
def cosine_similarity(a : list[float], b : list[float]):
    # 公式：两个向量点积 ÷ 各自模长的乘积。
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

# 保存一条记忆
async def save_vector_memory(r : Redis, user_id : int, text : str, vector : list[float]):
    await r.rpush(f"user:memories:{user_id}", json.dumps({"text": text, "vector": vector}))


# KNN全量遍历
async def recall_vector_memory(r : Redis, user_id : int, query_vector : list[float], topk : int, threshold : float):
    items = await r.lrange(f"user:memories:{user_id}", 0, -1)
    scored = []
    for item in items:
        data = json.loads(item)
        score = cosine_similarity(query_vector, data["vector"])
        if score >= threshold:
            scored.append((score, data["text"]))
    scored.sort(reverse=True)
    return [text for _, text in scored[:topk]]
