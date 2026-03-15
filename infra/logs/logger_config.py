"""
统一日志配置 - RAG Agent
"""
import logging
from pathlib import Path
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name: str, log_level: str = "INFO"):
    """
    统一的日志配置函数
    
    Args:
        name: 日志器名称
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        logger: 配置好的日志器
    """
    # 统一日志目录
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent
    log_dir = os.path.join(str(project_root), "logs")
    
    # 确保日志目录存在
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志器
    logger = logging.getLogger(name)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 设置日志级别
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    logger.setLevel(level_map.get(log_level.upper(), logging.INFO))
    
    # 文件处理器 - 统一日志文件
    log_file = os.path.join(log_dir, f"rag_agent_{name.lower()}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024*1024*10,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    
    # 统一格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str, log_level: str = "INFO"):
    """获取日志器的别名函数"""
    return setup_logger(name, log_level)
