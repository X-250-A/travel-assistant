"""ratelimit 注册中心 — 统一导出限流工具"""
from backend.app.ratelimit.core import check_rate_limit

__all__ = ["check_rate_limit"]
