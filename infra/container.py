from dotenv import load_dotenv

from agent.orchestrator.agent import DocAgent
from infra.config.app_config import AppConfig
from infra.logs.logger_config import get_logger
from rag.vector_store.pinecone_store import get_pinecone_store
from tools.langchain.registry import ToolRegistry

# Import tool modules so their decorators register them.
from tools.langchain import chart_gen, knowledge, summarizer  # noqa: F401

load_dotenv()

logger = get_logger("infra.container")


USE_PINECONE = True


class AppContainer:
    _doc_agent: DocAgent = None
    _vector_db = None
    _vector_db_type: str = None
    USE_PINECONE: bool = USE_PINECONE

    @classmethod
    def get_doc_agent(cls) -> DocAgent:
        if cls._doc_agent is None:
            vector_db = cls._get_vector_store()
            tools = cls._build_tools(vector_db)
            cls._doc_agent = DocAgent(tools)

        return cls._doc_agent

    @classmethod
    def _get_vector_store(cls):
        vector_db = get_pinecone_store()
        cls._vector_db = vector_db
        cls._vector_db_type = "pinecone"
        logger.info("Using Pinecone as vector store")
        return vector_db

    @classmethod
    def _build_tools(cls, vector_db):
        tools = {}
        dependencies = {}
        if vector_db is not None:
            dependencies["vector_store"] = vector_db

        for tool_name in ToolRegistry.list_all_tools():
            try:
                tool_instance = ToolRegistry.build_tool(tool_name, **dependencies)
                tools[tool_name] = tool_instance
                logger.debug(f"Built tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to build tool {tool_name}: {e}")
                raise

        logger.info(f"Built {len(tools)} tools from registry")
        return tools

    @classmethod
    def get_available_tool_names(cls):
        return ToolRegistry.list_all_tools()

    @classmethod
    def reload_vector_database(cls) -> None:
        if cls._vector_db_type == "pinecone":
            logger.info("Pinecone data is persisted remotely; skipping reload")
            return

        logger.warning("Vector DB type is not set; skipping reload")

    @classmethod
    def get_vector_database(cls):
        if cls._vector_db is None:
            cls._vector_db = get_pinecone_store()
            cls._vector_db_type = "pinecone"
        return cls._vector_db
