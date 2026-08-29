"""backend 包 — 惰性导出

注意：这里**不要** eager import `app`/`settings`。
若在包导入时急切 import backend.app，会导致 pydantic-settings 在测试
conftest 设置环境变量之前就创建 settings（读到的是 .env 而非测试环境变量），
从而破坏测试数据库/密钥隔离。
需要的模块请直接用完整路径导入，如 `from backend.app import settings`。
"""
