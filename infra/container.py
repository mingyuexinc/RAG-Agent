from agent.orchestrator.agent import DocAgent
from infra.config.app_config import AppConfig
from infra.logs.logger_config import get_logger
from rag.embeddings.embedding import build_embedding
from tools.generation.flow_chart import ChartGenTool
from tools.knowledge.search import KnowledgeSearchTool
from tools.knowledge.summarizer import SummaryTool
from rag.vector_store.faiss_store import get_or_create_vector_database, load_vector_database
from rag.vector_store.pinecone_store import get_pinecone_store

# 配置开关：使用哪个向量库
USE_PINECONE = True  # 设置为 True 使用 Pinecone，False 使用 FAISS

logger = get_logger("infra.container")

class AppContainer:
    _doc_agent: DocAgent = None
    _vector_db_type: str = None  # 记录当前使用的向量库类型
    USE_PINECONE: bool = USE_PINECONE  # 类属性，供外部访问

    @classmethod
    def get_doc_agent(cls) -> DocAgent:
        if cls._doc_agent is None:
            if cls.USE_PINECONE:
                # 使用 Pinecone
                vector_db = get_pinecone_store()
                cls._vector_db_type = "pinecone"
                logger.info("Using Pinecone as vector store")
            else:
                # 使用 FAISS
                vector_db = get_or_create_vector_database()
                cls._vector_db_type = "faiss"
                logger.info("Using FAISS as vector store")

            tools = {
                "knowledge_search": KnowledgeSearchTool(vector_db),
                "summarizer": SummaryTool(),
                "chart_gen": ChartGenTool(),
            }

            cls._doc_agent = DocAgent(tools)

        return cls._doc_agent

    @classmethod
    def reload_vector_database(cls) -> None:
        """
        重新加载向量数据库，用于处理新增文档后的情况
        
        Pinecone: 数据自动持久化，无需此操作
        FAISS: 需要重新从磁盘加载
        """
        if cls._vector_db_type == "pinecone":
            logger.info("Pinecone: Data is automatically persisted, no reload needed")
            return  # Pinecone 无需任何操作
        elif cls._vector_db_type == "faiss":
            logger.info("FAISS: Reloading vector database from disk...")
            embeddings = build_embedding()
            vector_db = load_vector_database(AppConfig.vector.VECTOR_DB_SAVE_PATH, embeddings)
            cls._vector_db = vector_db

            # 更新 agent 中的工具
            if cls._doc_agent:
                cls._doc_agent.tools["knowledge_search"] = KnowledgeSearchTool(vector_db)
        else:
            logger.warning("Vector DB type not set, skipping reload")


    @classmethod
    def get_vector_database(cls):
        """
        获取当前的向量数据库实例
        """
        if cls.USE_PINECONE:
            return get_pinecone_store()
        else:
            if cls._vector_db is None:
                cls._vector_db = get_or_create_vector_database()
            return cls._vector_db
