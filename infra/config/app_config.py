from infra.config.agent_config import AgentConfig
from infra.config.executor_config import ExecutorConfig
from infra.config.model_config import ModelConfig
from infra.config.prompt_config import PromptConfig
from infra.config.server_config import ServerConfig
from infra.config.vector_config import VectorConfig
from infra.config.pinecone_config import PineconeConfig
from infra.config.database_config import DatabaseConfig
from infra.config.mcp_config import MCPConfig


class AppConfig:
    model = ModelConfig
    agent = AgentConfig
    executor = ExecutorConfig()
    vector = VectorConfig()
    server = ServerConfig
    prompt = PromptConfig()
    pinecone = PineconeConfig()
    database = DatabaseConfig()
    mcp = MCPConfig()


