from langchain_community.vectorstores import FAISS

from core.executor import ExecutionContext
from model import ModelManager
from result.tool_result import ToolResult
from tools.base_tool import BaseTool


class KnowledgeSearchTool(BaseTool):
    name = "knowledge_search"
    input_keys = ["query"]
    output_key = "knowledge_search.result"

    def __init__(self, vector_store: FAISS):
        super().__init__(name=self.name)
        self.vector_store = vector_store

    def execute(self, context: ExecutionContext):
        try:
            query = context.get("query")
            docs = self.retrieve_with_score(self.vector_store, query, 5)
            result_data = {
                "documents": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": score
                    }
                    for doc, score in docs
                ]
            }
            result = ToolResult(
                success=True,
                data=result_data
            )
            context.set(self.output_key, result_data)
        except Exception as e:
            result = ToolResult(
                success=False,
                error=str(e),
                data={"documents": []}
            )
        return result.to_dict()

    def generate_query_variants(self, question: str):
        prompt = f"""
        请为下面的问题生成 3 个语义不同但相关的查询：
        {question}
        """
        model_manager = ModelManager(timeout=30)
        response = model_manager.invoke_with_timeout(prompt)
        return [q.strip("-• ") for q in response.content.split("\n") if len(q.strip()) > 0]

    def retrieve_with_score(self, db, query, k=5):
        retriever = db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k, "score_threshold": 0.0, "return_score": True}
        )
        return db.similarity_search_with_score(query, retriever=retriever)
