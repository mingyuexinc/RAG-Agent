import uvicorn

from infra.config.app_config import AppConfig

if __name__ == "__main__":
    server_config = AppConfig.server
    uvicorn.run(
        server_config.get_app_path(),
        host=server_config.HOST,
        port=server_config.get_port(),  # 使用方法而非属性
        reload=server_config.RELOAD
    )
