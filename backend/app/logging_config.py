import logging
from logging.handlers import RotatingFileHandler

from pathlib import Path




_configured = False
LOG_DIR = Path(__file__).parent / "logs"
FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"


def setup_logging():
    # 幂等操作
    global _configured
    if _configured:
        return

    # 创建文件
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 文件轮转
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(FORMAT))
    file_handler.setLevel(logging.INFO)

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(FORMAT))
    console_handler.setLevel(logging.INFO)

    root = logging.getLogger()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # 幂等操作二
    _configured = True


