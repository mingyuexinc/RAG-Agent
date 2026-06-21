"""
执行器配置

任务类型定义和任务模式schema。
工具与任务的映射关系现在由ToolRegistry动态管理，
不再使用硬编码的TASK_TOOL_CONSTRAINTS。
"""
from typing import Literal

from infra.config.base_config import BaseConfig

# 任务类型定义
TaskType = Literal[
    "knowledge_qa",
    "flowchart_generation",
    "summary",
    "context_analysis",
    "document_ingestion",
]

# 已弃用：硬编码的工具约束映射
# 现在使用ToolRegistry.get_tools_for_task(task_type)动态获取
# TASK_TOOL_CONSTRAINTS 已移除，请使用ToolRegistry


class ExecutorConfig(BaseConfig):
    """
    执行器配置类
    
    注意：工具与任务的映射不再在此硬编码，
    而是通过tools.langchain.registry.ToolRegistry动态管理。
    使用ToolRegistry.register装饰器注册工具时会自动建立任务映射。
    """
    
    # JSON任务模式 - 用于LLM理解和生成任务计划
    JSON_TASK_SCHEMA = """
    {
      "task_type": "knowledge_qa | flowchart_generation | summary | context_analysis | document_ingestion",
      "need_tools": true,
      "tools": ["knowledge_search", "summarizer", "chart_gen", "document_parser"],
      "tool_params": {
         "knowledge_search": {
            "query": "string",
            "top_k": 5,
            "filters": {}
         },
         "summarizer": {
            "documents": "knowledge_search.result.documents"
         },
         "chart_gen": {
            "summarized_text": "summarizer.result"
         },
         "document_parser": {
            "file_path": "string",
            "filename": "string",
            "page_ranges": "optional string",
            "ocr_language": "optional string",
            "parse_mode": "auto"
         }
      }
    }
    """
