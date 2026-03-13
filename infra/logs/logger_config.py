import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name:str,log_dir:str = "./logs/log_data"):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir,exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, f"{name}.log"),
        maxBytes=1024*1024*10,
        backupCount=5,
        encoding='utf-8'  # 关键：指定 UTF-8 编码
    )

    console_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger