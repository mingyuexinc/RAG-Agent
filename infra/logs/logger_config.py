"""
统一日志配置 - RAG Agent
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional

# 全局变量，存储已初始化的logger
_initialized_loggers: Dict[str, logging.Logger] = {}
_log_dir: Optional[str] = None
_initialized = False


def initialize_log_system():
    """初始化日志系统 - 在应用入口处调用"""
    global _initialized, _log_dir
    
    if _initialized:
        return
    
    # 用 cwd，避免 __file__ 坑
    _log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(_log_dir, exist_ok=True)
    _initialized = True
    
    # 升级所有已存在的临时logger
    for name, logger in list(_initialized_loggers.items()):
        # 移除临时控制台处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 重新创建完整的logger
        _create_logger(name, "INFO")


def get_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    获取日志器 - 支持延迟初始化
    
    Args:
        name: 日志器名称
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        logger: 配置好的日志器
    """
    # 检查是否已经初始化过这个logger
    if name in _initialized_loggers:
        return _initialized_loggers[name]
    
    # 如果日志系统未初始化，返回一个临时的控制台logger
    if not _initialized:
        # 创建临时的控制台logger
        logger = logging.getLogger(name)
        if not logger.handlers:
            # 只添加控制台处理器
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # 缓存临时logger
        _initialized_loggers[name] = logger
        return logger
    
    # 正常初始化流程
    return _create_logger(name, log_level)


def _create_logger(name: str, log_level: str) -> logging.Logger:
    """创建完整的日志器（包含文件处理器）"""
    # 创建日志器
    logger = logging.getLogger(name)
    
    # 避免重复添加handler
    if logger.handlers:
        _initialized_loggers[name] = logger
        return logger
    
    # 设置日志级别
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 文件处理器
    if _log_dir:
        log_file = os.path.join(_log_dir, f"rag_agent_{name.lower()}.log")
        
        # 👇 delay=True 防止初始化时报错
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8',
            delay=True
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        
        # 统一格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    # 缓存logger
    _initialized_loggers[name] = logger
    
    return logger


# 清理函数（用于测试）
def _reset_log_system():
    """重置日志系统 - 仅用于测试"""
    global _initialized, _log_dir, _initialized_loggers
    _initialized = False
    _log_dir = None
    _initialized_loggers.clear()
