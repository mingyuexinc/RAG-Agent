import base64
import os

from typing import Dict, Any
from fastapi import HTTPException
from agent.orchestrator.agent import DocAgent
from agent.orchestrator.executor import ExecutionResult
from agent.prompts.prompt_manager import PromptManager
from agent.state.state_manager import AgentState
from app.api.schemas_response import QueryRequest, QueryResponse
from infra.config.app_config import AppConfig
from services.cache_manager import cache_manager
from services.image_service import get_image_service

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

    async def generate(
        self,
        result: ExecutionResult,
        doc_agent: DocAgent,
        query: str,
        state:AgentState
    ) -> Dict[str, Any]:
        if result.task_type == "knowledge_qa":
            return self._knowledge_qa(result, doc_agent, query,state)
        elif result.task_type == "flowchart_generation":
            return await self._flowchart(result)
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
            AppConfig.prompt.TEMPLATE_KNOWLEDGE_QA,
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



    async def _flowchart(self, result: ExecutionResult) -> Dict[str, Any]:
        """处理流程图生成响应（base64兼容版）"""
        chart_result = result.tool_results["chart_gen"]
        chart_data = chart_result["data"]
        chart_url = chart_data.get("chart_url")

        if not chart_url:
            return {
                "task_type": result.task_type,
                "answer": "流程图生成失败：未获取到图表URL。",
                "payload": None
            }

        try:
            image_service = get_image_service()
            image_result = await image_service.process_flowchart_image(chart_url)

            if image_result["success"]:
                local_path = image_result.get("local_path")

                # ✅ 核心：读取图片 → base64
                image_base64 = None
                if local_path and os.path.exists(local_path):
                    with open(local_path, "rb") as f:
                        image_base64 = base64.b64encode(f.read()).decode()

                # 更新缓存
                cache_manager.add_entry(
                    chart_url,
                    local_path,
                    image_result.get("file_size", 0)
                )

                response_data = {
                    "task_type": result.task_type,
                    "answer": "已根据制度文档生成流程图。",
                    "payload": {
                        "chart_url": chart_url,
                        "chart_code": chart_data.get("chart_code"),
                        "image_base64": image_base64,  # ✅ 关键字段
                        "cached": image_result.get("cached", False),
                        "file_size": image_result.get("file_size", 0)
                    }
                }

                # 压缩信息（可选）
                if not image_result.get("cached", False):
                    response_data["payload"]["compression_info"] = {
                        "original_size": image_result.get("original_size", 0),
                        "optimized_size": image_result.get("optimized_size", 0),
                        "compression_ratio": image_result.get("compression_ratio", 0)
                    }

                return response_data

            else:
                return {
                    "task_type": result.task_type,
                    "answer": f"流程图处理失败：{image_result.get('error', '未知错误')}",
                    "payload": {
                        "chart_url": chart_url,
                        "chart_code": chart_data.get("chart_code"),
                        "image_base64": None,
                        "error": image_result.get("error")
                    }
                }

        except Exception as e:
            from infra.logs.logger_config import get_logger
            logger = get_logger("agent.response")
            logger.error(f"流程图图片处理失败: {e}", exc_info=True)

            return {
                "task_type": result.task_type,
                "answer": "流程图生成过程中出现错误，请稍后重试。",
                "payload": {
                    "chart_url": chart_url,
                    "chart_code": chart_data.get("chart_code"),
                    "image_base64": None,
                    "error": str(e)
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

async def process_tool_result(
    result: ExecutionResult,
    doc_agent: DocAgent,
    request: QueryRequest,
    state: AgentState
):
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    result_generator = ResponseGenerator()

    response_data = await result_generator.generate(
        result=result,
        doc_agent=doc_agent,
        query=request.query,
        state=state
    )

    # ✅ 强制结构标准化
    normalized_response = {
        "task_type": response_data.get("task_type", "unknown"),
        "answer": response_data.get("answer", ""),
        "payload": response_data.get("payload", {}),
        "usage_metadata": response_data.get("usage_metadata", None)
    }

    # ✅ 保存对话
    state.add_conversation_turn(
        query=request.query,
        response=normalized_response["answer"]
    )
    doc_agent.state_manager.save(state)

    return QueryResponse(**normalized_response)
