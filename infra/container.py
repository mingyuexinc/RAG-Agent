from agent.orchestrator.agent import DocAgent
from tools.generation.flow_chart import ChartGenTool
from tools.knowledge.search import KnowledgeSearchTool
from tools.knowledge.summarizer import SummaryTool
from rag.vector_store.faiss_store import get_or_create_vector_database


class AppContainer:
    _doc_agent: DocAgent = None

    @classmethod
    def get_doc_agent(cls) -> DocAgent:
        if cls._doc_agent is None:
            vector_db = get_or_create_vector_database()

            tools = {
                "knowledge_search": KnowledgeSearchTool(vector_db),
                "summarizer": SummaryTool(),
                "chart_gen": ChartGenTool(),
            }

            cls._doc_agent = DocAgent(tools)

        return cls._doc_agent