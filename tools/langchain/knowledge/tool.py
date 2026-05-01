"""
知识检索工具实现
使用装饰器自动注册到ToolRegistry
"""
from typing import Any, Dict

from langchain_core.tools import StructuredTool

from rag.retrieval.vector_retriever import retrieve_with_score
from ..base import BaseLangChainTool
from ..registry import ToolRegistry
from .input import KnowledgeSearchInput


@ToolRegistry.register(
    name="knowledge_search",
    task_types=["knowledge_qa", "flowchart_generation", "summary"],
    dependencies=["vector_store"],
    description="根据query从向量知识库检索相关文档"
)
class KnowledgeSearchTool(BaseLangChainTool):
    """知识检索工具 - 自动注册"""
    
    # 类属性将在装饰器中被自动设置
    name = "knowledge_search"
    description = "根据query从向量知识库检索相关文档"
    task_types = ["knowledge_qa", "flowchart_generation", "summary"]
    dependencies = ["vector_store"]
    metadata = {
        "output_key": "knowledge_search.result",
        "set_inputs_to_context": True,
        "input_keys": ["query"],
    }
    
    def execute(self, query: str) -> Dict[str, Any]:
        """执行知识检索"""
        try:
            docs = retrieve_with_score(self.vector_store, query, 5)
            result_data = {
                "documents": [
                    {
                        "content": doc.page_content if hasattr(doc, "page_content") else str(doc),
                        "metadata": doc.metadata if hasattr(doc, "metadata") else {},
                        "score": score,
                    }
                    for doc, score in docs
                ]
            }
            return self.handle_success(result_data)
        except Exception as exc:
            return self.handle_error(exc)


def build_knowledge_search_tool(vector_store) -> StructuredTool:
    """构建知识检索工具"""
    tool = KnowledgeSearchTool(vector_store=vector_store)
    
    return StructuredTool.from_function(
        func=tool.execute,
        name=tool.name,
        description=tool.description,
        args_schema=KnowledgeSearchInput,
        metadata={
            "output_key": "knowledge_search.result",
            "set_inputs_to_context": True,
            "input_keys": ["query"],
        },
    )
