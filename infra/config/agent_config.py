from infra.config.base_config import BaseConfig


class AgentConfig(BaseConfig):
    MAX_STEPS = 5
    MAX_RETRIES = 3
    MAX_CONTENT_SIZE = 100
    SESSION_TIMEOUT = 3600
