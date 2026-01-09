from pathlib import Path

from config.base_config import BaseConfig


class VectorConfig(BaseConfig):
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    FILE_LOAD_PATH = str(PROJECT_ROOT / "assets" / "upload")
    VECTOR_DB_SAVE_PATH = str(PROJECT_ROOT / "vector_db")

    # text splitter
    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 128

    # support file type
    FILE_SUFFIX = ["pdf", "doc", "docx", "txt"]