import re
from dataclasses import dataclass

from redis.asyncio import Redis

from backend.app import settings
from backend.app.schemas.llm_output import PrefType

PREFERENCE_PATTERNS = [
    # (PrefType, 正则, 取值回调)
    (
        PrefType.DIET,
        r"不(?:吃|要|碰|忌)([^，。?!\s]{1,4})",
        lambda m: f"忌口{m.group(1)}",
    ),  # "不吃辣" → 忌口辣
    (
        PrefType.BUDGET,
        r"预算(?:大约|大概|最多)?(\d+)\s*元?",
        lambda m: f"上限{m.group(1)}",
    ),  # "预算3000元" → 上限3000元
    (
        PrefType.MOBILITY,
        r"不(?:想|要|喜欢|爱)(爬山|暴走|走远路)",
        lambda m: f"不想{m.group(1)}",
    ),  # "不想爬山"
    (PrefType.PACE, r"不(?:想|要|喜欢)(赶|太赶|紧凑)", lambda m: f"{m.group(1)}"),  # "不要赶行程"
]

MERGE_RULES: dict[PrefType, str] = {
    PrefType.DIET: "add",
    PrefType.BUDGET: "replace",
    PrefType.MOBILITY: "replace",
    PrefType.PACE: "replace",
}


@dataclass
class Preferences:
    type: PrefType
    value: str


def merge_prefs(old: dict[str, str], new_prefs: list[Preferences]) -> dict[str, str]:
    result = dict(old)
    for p in new_prefs:
        merge = MERGE_RULES.get(p.type, "replace")
        if merge == "add":
            # 旧值逗号拆开，加新值，去重，再拼回
            existing = set(result.get(p.type, "").split(",")) if result.get(p.type) else set()
            existing.add(p.value)
            result[p.type] = ",".join(sorted(existing))
        else:
            result[p.type] = p.value
    return result


# 正则提取用户偏好，用于做跨会话长期记忆
def extract_preferences(text: str) -> list[Preferences]:
    preferences = []
    for ptype, pattern, callback in PREFERENCE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            preferences.append(Preferences(type=ptype, value=callback(m)))
    return preferences


# 存储所提取的偏好
async def save_preferences(r: Redis, user_id: int, pref: list[Preferences]) -> None:
    # 归一化key
    key = f"user:preferences:{user_id}"
    old = await r.hgetall(key)
    merged = merge_prefs(old, pref)
    if merged:
        await r.hmset(key, merged)
    await r.expire(key, settings.PERMANENT_SESSION_LIFETIME)


# 加载偏好
async def load_preferences(r: Redis, user_id: int):
    return await r.hgetall(f"user:preferences:{user_id}")
