from abc import ABC, abstractmethod


class BaseLoader(ABC):
    """文档加载器抽象基类"""

    @abstractmethod
    def load(self, file_path: str) -> str:
        """加载文档内容"""
        pass