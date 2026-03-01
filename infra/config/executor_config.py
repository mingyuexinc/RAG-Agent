from typing import Literal

from infra.config.base_config import BaseConfig

TaskType = Literal[
    "knowledge_qa",
    "flowchart_generation",
    "summary",
    "context_analysis"
]

TASK_TOOL_CONSTRAINTS = {
    "knowledge_qa": ["knowledge_search"],
    "flowchart_generation": ["knowledge_search", "summarizer", "chart_gen"],
    "summary": ["knowledge_search", "summarizer"],
    "context_analysis": [],  # 上下文分析任务不需要工具
}

class ExecutorConfig(BaseConfig):
    TASK_TOOL_CONSTRAINTS = TASK_TOOL_CONSTRAINTS
    JSON_TASK_SCHEMA = """
    {
      "task_type": "knowledge_qa | flowchart_generation | summary | context_analysis",
      "need_tools": true,
      "tools": ["knowledge_search", "summarizer", "chart_gen"],
      "tool_params": {
         "knowledge_search": {
            "query": "string"
         },
         "summarizer": {
            "documents": "knowledge_search.result.documents"
         },
         "chart_gen": {
            "summarized_text": "summarizer.result"
         }
      }
    }
    """
