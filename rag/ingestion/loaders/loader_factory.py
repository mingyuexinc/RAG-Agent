import logging
from typing import Optional

from infra.logs.logger_config import setup_logger
from rag.ingestion.loaders.base_loader import BaseLoader
from rag.ingestion.loaders.pdf_loader import PDFLoader
from rag.ingestion.loaders.text_loader import TextLoader


logger = setup_logger("rag.ingestion.loaders")

class LoaderFactory:
    """文档加载器工厂"""
    
    @staticmethod
    def create_loader(file_path: str, filename: Optional[str] = None) -> BaseLoader:
        """根据文件类型创建合适的加载器"""
        
        # 获取文件扩展名
        if filename:
            extension = filename.split('.')[-1].lower()
        else:
            extension = file_path.split('.')[-1].lower()
        
        logger.info(f"为文件 {filename or file_path} (扩展名: {extension}) 创建加载器")
        
        # 根据扩展名选择加载器
        if extension in ['pdf']:
            logger.info("使用PDF加载器")
            return PDFLoader()
        elif extension in ['txt', 'text', 'md', 'markdown']:
            logger.info("使用文本加载器")
            return TextLoader()
        else:
            # 默认使用文本加载器
            logger.warning(f"未知文件类型 {extension}，默认使用文本加载器")
            return TextLoader()


def get_loader(file_path: str, filename: Optional[str] = None) -> BaseLoader:
    """获取合适的文档加载器"""
    return LoaderFactory.create_loader(file_path, filename)
