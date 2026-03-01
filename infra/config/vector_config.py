from pathlib import Path

from infra.config.base_config import BaseConfig


class VectorConfig(BaseConfig):
    # 基于配置文件位置动态计算项目根目录
    @classmethod
    def _get_project_root(cls) -> Path:
        """获取项目根目录"""
        return Path(__file__).resolve().parent.parent.parent

    @classmethod
    def _get_data_root(cls) -> Path:
        """获取数据根目录"""
        return cls._get_project_root() / "data"

    @property
    def FILE_LOAD_PATH(self) -> str:
        """文件上传目录"""
        upload_dir = self._get_data_root() / "upload"
        # 确保目录存在
        upload_dir.mkdir(parents=True, exist_ok=True)
        return str(upload_dir)

    @property
    def VECTOR_DB_SAVE_PATH(self) -> str:
        """向量数据库保存目录"""
        vector_dir = self._get_data_root() / "vector_store"
        # 确保目录存在
        vector_dir.mkdir(parents=True, exist_ok=True)
        return str(vector_dir)

    # text splitter
    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 128

    # support file type
    FILE_SUFFIX = ["pdf", "doc", "docx", "txt"]