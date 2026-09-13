import time

from backend.app.logging_config import logger

from fastapi import Request

async def timing_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
    finally:
        end_time = time.perf_counter()
        elapsed_time = (end_time - start_time) * 1000
        logger.info(
            "request time=%.1f ms, path=%s, method=%s", elapsed_time, request.url.path, request.method
        )
    return response
