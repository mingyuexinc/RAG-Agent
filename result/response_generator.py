from typing import Dict, Any, Optional
from core.agent import DocAgent
from core.executor import ExecutionResult, TaskType
from fastapi import HTTPException

from core.session.state_manager import AgentState
from prompts.prompt_manager import PromptManager
from result.response_api import QueryRequest, QueryResponse


class ResponseGenerator:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResponseGenerator, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.pm = PromptManager()
            self._initialized = True


    def generate(
        self,
        result: ExecutionResult,
        doc_agent: DocAgent,
        query: str,
        state:AgentState
    ) -> Dict[str, Any]:
        if result.task_type == "knowledge_qa":
            return self._knowledge_qa(result, doc_agent, query,state)

        elif result.task_type == "flowchart_generation":
            return self._flowchart(result)

        elif result.task_type == "context_analysis":
            return self._context_analysis(doc_agent, query, state)
        else:
            raise ValueError(f"Unsupported task_type: {result.task_type}")


    def _knowledge_qa(
            self,
            result: ExecutionResult,
            doc_agent: DocAgent,
            query: str,
            state: AgentState
    ) -> Dict[str, Any]:
        prompt = self.pm.render(
            "templates/knowledge_qa_template.txt",
            context=state.working_context.data,
            query = query
        )

        answer = doc_agent.generate_response(prompt)
        knowledge_search_result = result.tool_results["knowledge_search"]
        documents = knowledge_search_result["data"]["documents"]
        references = [doc.get("content", "") for doc in documents]
        metadata = [doc.get("metadata", {}) for doc in documents]

        return {
            "task_type":result.task_type,
            "answer": answer,
            "references": references,
            "usage_metadata": metadata
        }


    def _flowchart(self,result: ExecutionResult) -> Dict[str, Any]:

        chart_result = result.tool_results["chart_gen"]
        chart_data = chart_result["data"]

        return {
            "task_type":result.task_type,
            "answer": "已根据制度文档生成流程图。",
            "payload": {
                "chart_url": chart_data.get("chart_url"),
                "chart_code": chart_data.get("chart_code")
            }
        }

    def _context_analysis(self, doc_agent, query, state) -> Dict[str, Any]:
        if not state.working_context:
            return {
                "answer": "当前没有可用的上下文数据进行分析。",
                "task_type": "context_analysis"
            }

        state_view = state.to_prompt_view("context_analysis")

        prompt = self.pm.render(
            "templates/context_analysis_template.txt",
            query=query,
            **state_view
        )

        llm_response = doc_agent.generate_response(prompt)

        return {
            "answer": llm_response,
            "task_type": "context_analysis"
        }



def process_tool_result(
    result: ExecutionResult,
    doc_agent: DocAgent,
    request: QueryRequest,
    state:AgentState
):
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    result_generator = ResponseGenerator()

    response_data = result_generator.generate(
        result=result,
        doc_agent=doc_agent,
        query=request.query,
        state=state
    )

    state.add_conversation_turn(
        query=request.query,
        response=response_data.get("answer", "")
    )
    doc_agent.state_manager.save(state)

    return QueryResponse(**response_data)
