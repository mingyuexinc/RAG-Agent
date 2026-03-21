import logging
from typing import Tuple, List

from infra.logs.logger_config import get_logger
from rag.ingestion.loaders.base_loader import BaseLoader
from rag.ingestion.splitters.fixed_size_splitter import fixed_size_splitter


logger = get_logger("rag.ingestion.loaders")

class TextLoader(BaseLoader):
    """文本文档加载器"""

    def load(self, file_path: str) -> str:
        """加载文本文档"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            
            logger.info(f"成功加载文本文件: {file_path}, 字符数: {len(text)}")
            return text
            
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    text = file.read()
                logger.info(f"成功加载文本文件(GBK编码): {file_path}, 字符数: {len(text)}")
                return text
            except Exception as e:
                logger.error(f"无法读取文本文件 {file_path}: {e}")
                raise
        
        except Exception as e:
            logger.error(f"加载文本文件失败 {file_path}: {e}")
            raise

    def load_and_split(self, file_path: str) -> List[str]:
        """加载并分割文本文档"""
        text = self.load(file_path)
        return fixed_size_splitter(text)
