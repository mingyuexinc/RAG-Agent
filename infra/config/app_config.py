from infra.config.agent_config import AgentConfig
from infra.config.executor_config import ExecutorConfig
from infra.config.model_config import ModelConfig
from infra.config.prompt_config import PromptConfig
from infra.config.server_config import ServerConfig
from infra.config.vector_config import VectorConfig


class AppConfig:
    model = ModelConfig
    agent = AgentConfig
    executor = ExecutorConfig()
    vector = VectorConfig()
    server = ServerConfig
    prompt = PromptConfig()


