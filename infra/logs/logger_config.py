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
    import tempfile
    
    # 统一日志目录 - 使用多重备选方案
    # 方案1: 项目根目录
    project_root = Path(__file__).parent.parent.parent
    log_dir = os.path.join(str(project_root), "logs")
    
    # 方案2: 临时目录（备选）
    temp_log_dir = os.path.join(tempfile.gettempdir(), "rag_agent_logs")
    
    # 尝试创建日志目录
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        final_log_dir = log_dir
    except (OSError, PermissionError) as e:
        print(f"警告: 无法创建项目日志目录 {log_dir}: {e}")
        print(f"使用临时目录: {temp_log_dir}")
        try:
            if not os.path.exists(temp_log_dir):
                os.makedirs(temp_log_dir, exist_ok=True)
            final_log_dir = temp_log_dir
        except Exception as e2:
            print(f"错误: 无法创建临时日志目录 {temp_log_dir}: {e2}")
            # 最后备选：只使用控制台输出
            final_log_dir = None
    
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
    
    # 控制台处理器（总是添加）
    console_handler = logging.StreamHandler()
    
    # 统一格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果可以创建目录）
    if final_log_dir:
        try:
            log_file = os.path.join(final_log_dir, f"rag_agent_{name.lower()}.log")
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=1024*1024*10,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            print(f"日志文件: {log_file}")
        except Exception as e:
            print(f"警告: 无法创建日志文件，仅使用控制台输出: {e}")
    else:
        print("信息: 仅使用控制台输出")
    
    return logger


def get_logger(name: str, log_level: str = "INFO"):
    """获取日志器的别名函数"""
    return setup_logger(name, log_level)
