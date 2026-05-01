import os

import uvicorn

from infra.config.app_config import AppConfig
from infra.logs.logger_config import initialize_log_system


def _reload_enabled(default: bool) -> bool:
    value = os.getenv("RAG_AGENT_RELOAD")
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    initialize_log_system()
    server_config = AppConfig.server
    uvicorn.run(
        "api.routes:app",
        host=server_config.HOST,
        port=server_config.get_port(),
        reload=_reload_enabled(server_config.RELOAD),
    )
