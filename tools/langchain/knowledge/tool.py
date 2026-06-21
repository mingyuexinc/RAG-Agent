from typing import Any, Dict, Optional

from langchain_core.tools import StructuredTool

from rag.retrieval.vector_retriever import retrieve_with_score
from ..base import BaseLangChainTool
from ..registry import ToolRegistry
from .input import KnowledgeSearchInput


@ToolRegistry.register(
    name="knowledge_search",
    task_types=["knowledge_qa", "flowchart_generation", "summary"],
    dependencies=["vector_store"],
    description="Retrieve already-indexed knowledge chunks from the vector store",
)
class KnowledgeSearchTool(BaseLangChainTool):
    """Vector retrieval tool for indexed RAG content."""

    name = "knowledge_search"
    description = "Retrieve already-indexed knowledge chunks from the vector store"
    task_types = ["knowledge_qa", "flowchart_generation", "summary"]
    dependencies = ["vector_store"]
    metadata = {
        "output_key": "knowledge_search.result",
        "set_inputs_to_context": True,
        "input_keys": ["query"],
    }

    def execute(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            docs = retrieve_with_score(self.vector_store, query, top_k, filters or {})
            result_data = {
                "documents": [
                    {
                        "content": doc.page_content if hasattr(doc, "page_content") else str(doc),
                        "metadata": _normalize_document_metadata(
                            doc.metadata if hasattr(doc, "metadata") else {}
                        ),
                        "score": score,
                    }
                    for doc, score in docs
                ]
            }
            return self.handle_success(result_data)
        except Exception as exc:
            return self.handle_error(exc)


def build_knowledge_search_tool(vector_store) -> StructuredTool:
    tool = KnowledgeSearchTool(vector_store=vector_store)

    return StructuredTool.from_function(
        func=tool.execute,
        name=tool.name,
        description=tool.description,
        args_schema=KnowledgeSearchInput,
        metadata=tool.metadata,
    )


def _normalize_document_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(metadata or {})
    normalized.setdefault("title", normalized.get("source", ""))
    normalized.setdefault("heading", normalized.get("section_path", ""))
    normalized.setdefault("section_path", normalized.get("heading", ""))
    normalized.setdefault("page_number", None)
    normalized.setdefault("block_type", "chunk")
    return normalized
