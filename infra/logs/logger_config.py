"""
统一日志配置 - RAG Agent
"""

def setup_logger(name: str, log_level: str = "INFO"):
    import os
    import logging
    from logging.handlers import RotatingFileHandler

    # 用 cwd，避免 __file__ 坑
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    log_file = os.path.join(log_dir, f"rag_agent_{name.lower()}.log")

    # 👇 delay=True 防止初始化时报错
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
        delay=True
    )

    console_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str, log_level: str = "INFO"):
    """获取日志器的别名函数"""
    return setup_logger(name, log_level)
