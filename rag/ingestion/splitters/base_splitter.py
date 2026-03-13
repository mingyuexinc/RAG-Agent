from abc import ABC, abstractmethod
from typing import List
from rag.ingestion.splitters.fixed_size_splitter import fixed_size_splitter


class BaseSplitter(ABC):
    """文档切片器抽象基类"""

    @abstractmethod
    def split(self, text: str) -> List[str]:
        """切片文档"""
        pass

class TextSplitter(BaseSplitter):
    """文本切片器"""

    def split(self, text: str) -> List[str]:
        """切片文本"""
        return fixed_size_splitter(text)