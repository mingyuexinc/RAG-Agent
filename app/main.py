import uvicorn

from infra.config.app_config import AppConfig

if __name__ == "__main__":
    server_config = AppConfig.server
    uvicorn.run(
        server_config.get_app_path(),
        host=server_config.HOST,
        port=server_config.PORT,
        reload=server_config.RELOAD
    )
