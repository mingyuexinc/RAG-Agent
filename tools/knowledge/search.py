from typing import Dict, Any, Optional

from agent.orchestrator.executor import ExecutionContext
from agent.response.tool_result import ToolResult
from infra.logs.logger_config import setup_logger
from tools.base import BaseTool
from rag.retrieval.vector_retriever import retrieve_with_score

logger = setup_logger("knowledge_search")


class KnowledgeSearchTool(BaseTool):
    name = "knowledge_search"
    input_keys = ["query"]
    output_key = "knowledge_search.result"

    def __init__(self, vector_store, filter_metadata: Optional[Dict[str, Any]] = None):
        """
        初始化工具

        :param vector_store: FAISS 对象或 PineconeStore 对象
        """
        super().__init__(name=self.name)
        self.vector_store = vector_store

        # 检测向量库类型，仅用于日志
        self._is_pinecone = self._check_if_pinecone(vector_store)

        logger.info(
            f"KnowledgeSearchTool initialized with {'Pinecone' if self._is_pinecone else 'FAISS'} backend"
        )
        logger.info("Using rule-based metadata filtering")

    def _check_if_pinecone(self, vector_store) -> bool:
        """检查是否是 Pinecone Store"""
        try:
            from rag.vector_store.pinecone_store import PineconeStore
            return isinstance(vector_store, PineconeStore)
        except Exception:
            return False

    def execute(self, context: ExecutionContext):
        try:
            query = context.get("query")

            logger.info(f"Searching for query: {query}")

            if self._is_pinecone:
                # Pinecone: 获取统计信息
                stats = self.vector_store.get_stats()
                logger.info(
                    f"Pinecone index stats: {stats.get('vector_count', 'unknown')} vectors"
                )
            else:
                # FAISS: 获取向量数量
                logger.info(
                    f"Vector store has {self.vector_store.index.ntotal} vectors"
                )

            # 使用统一的向量检索模块
            docs = retrieve_with_score(self.vector_store, query, 5)

            logger.info(f"Retrieved {len(docs)} documents")

            for i, (doc, score) in enumerate(docs):
                source = (
                    doc.metadata.get("source", "unknown")
                    if hasattr(doc, "metadata")
                    else "unknown"
                )
                doc_type = doc.metadata.get("document_type", "unknown")

                logger.info(
                    f"Doc {i+1}: score={score:.4f}, source={source}, type={doc_type}"
                )

                content_preview = (
                    doc.page_content[:100].replace("\n", " ").strip()
                    if hasattr(doc, "page_content")
                    else str(doc)[:100]
                )

                logger.info(f"Doc {i+1} content_preview: {content_preview}...")

            result_data = {
                "documents": [
                    {
                        "content": doc.page_content
                        if hasattr(doc, "page_content")
                        else str(doc),
                        "metadata": doc.metadata if hasattr(doc, "metadata") else {},
                        "score": score,
                    }
                    for doc, score in docs
                ]
            }

            result = ToolResult(success=True, data=result_data)

            context.set(self.output_key, result_data)

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)

            result = ToolResult(
                success=False,
                error=str(e),
                data={"documents": []},
            )

        return result.to_dict()

