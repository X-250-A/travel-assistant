"""memory 注册中心 — 统一导出偏好记忆与向量记忆"""
from backend.app.memory.preferences import (
    Preferences,
    extract_preferences,
    load_preferences,
    merge_prefs,
    save_preferences,
)
from backend.app.memory.vector_memory import (
    cosine_similarity,
    recall_vector_memory,
    save_vector_memory,
)

__all__ = [
    "Preferences",
    "merge_prefs",
    "extract_preferences",
    "save_preferences",
    "load_preferences",
    "cosine_similarity",
    "save_vector_memory",
    "recall_vector_memory",
]
