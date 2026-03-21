import sys
from pathlib import Path

from infra.config.base_config import BaseConfig


class ServerConfig(BaseConfig):
    # API应用配置
    APP_MODULE = "api.routes"
    APP_INSTANCE = "app"

    # 服务器配置
    HOST = "127.0.0.1"
    
    @classmethod
    def get_port(cls):
        """根据环境返回不同端口"""
        import os
        # 简单检测：如果在/home/studio_service下，就是ModelScope环境
        if '/home/studio_service' in os.getcwd() or '/home/studio_service' in os.getenv('PWD', ''):
            return 8001
        else:
            return 8000
    
    PORT = get_port()  # 动态端口
    RELOAD = True

    # 基于当前文件位置动态计算模块路径
    @classmethod
    def _get_relative_api_path(cls) -> str:
        """
        基于配置文件位置计算API模块的相对路径
        """
        # 获取当前配置文件的路径
        config_file = Path(__file__).resolve()
        # 获取项目根目录 (infra/config的父目录的父目录)
        project_root = config_file.parent.parent.parent

        # 获取API路由文件的路径
        api_routes_file = project_root / "app" / "api" / "routes.py"

        if api_routes_file.exists():
            # 计算相对于项目根目录的导入路径
            sys.path.insert(0, str(project_root))
            return "app.api.routes:app"
        else:
            # 备用方案
            return "api.routes:app"

    @classmethod
    def get_app_path(cls) -> str:
        """获取应用路径字符串"""
        return cls._get_relative_api_path()


