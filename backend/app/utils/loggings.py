import logging
import functools

logger = logging.getLogger(__name__)

def crud_logger(level=logging.INFO, action=""):
    def decorate(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                logger.exception("crud failed, action=%s fn=%s", action, func.__name__)
                raise
            logger.log(level, "crud flushed action=%s fn=%s",action, func.__name__)
            return result
        return wrapper
    return decorate