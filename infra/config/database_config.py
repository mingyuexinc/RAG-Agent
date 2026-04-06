from pathlib import Path
from infra.config.base_config import BaseConfig


class DatabaseConfig(BaseConfig):
    """数据库配置类，遵循项目工程规范"""
    
    @classmethod
    def _get_project_root(cls) -> Path:
        """获取项目根目录"""
        return Path(__file__).resolve().parent.parent.parent
    
    @classmethod
    def _get_data_root(cls) -> Path:
        """获取数据根目录"""
        return cls._get_project_root() / "data"
    
    @property
    def DATABASE_PATH(self) -> str:
        """SQLite数据库文件路径"""
        db_dir = self._get_data_root() / "database"
        # 确保目录存在
        db_dir.mkdir(parents=True, exist_ok=True)
        db_file = db_dir / "rag_agent.db"
        return str(db_file)
    
    @property
    def BACKUP_PATH(self) -> str:
        """数据库备份目录"""
        backup_dir = self._get_data_root() / "database" / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return str(backup_dir)
    
    # 数据库连接配置
    ECHO_SQL = False  # 是否打印SQL语句
    POOL_SIZE = 5     # 连接池大小
    MAX_OVERFLOW = 10 # 连接池溢出大小
    
    # 数据库配置
    DEFAULT_TIMEOUT = 30  # 默认超时时间(秒)
    FOREIGN_KEYS = True    # 启用外键约束
