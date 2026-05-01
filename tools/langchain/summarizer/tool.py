"""
摘要工具实现
使用装饰器自动注册到ToolRegistry
"""
from typing import Any, Dict, List

from langchain_core.tools import StructuredTool

from agent.prompts.prompt_manager import PromptManager
from infra.config.app_config import AppConfig
from llm.model import ModelManager
from ..base import BaseLangChainTool
from ..registry import ToolRegistry
from .input import SummarizerInput


@ToolRegistry.register(
    name="summarizer",
    task_types=["flowchart_generation", "summary"],
    dependencies=[],  # summarizer不需要外部依赖
    description="对检索文档进行总结生成摘要"
)
class SummarizerTool(BaseLangChainTool):
    """摘要工具 - 自动注册"""
    
    name = "summarizer"
    description = "对检索文档进行总结生成摘要"
    task_types = ["flowchart_generation", "summary"]
    dependencies = []
    metadata = {
        "output_key": "summarizer.result",
        "set_inputs_to_context": False,
        "input_keys": ["documents"],
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prompt_manager = PromptManager()
        self.model_manager = ModelManager(timeout=30)
    
    def execute(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行文档摘要"""
        try:
            content = "\n".join([doc.get("content", "") for doc in documents]).strip()
            if not content:
                raise ValueError("No content found in documents")

            summarizer_prompt = self.prompt_manager.render(
                AppConfig.prompt.TEMPLATE_SUMMARIZER,
                content=content,
                max_length=500,
            )
            response = self.model_manager.invoke_with_timeout(summarizer_prompt)
            summary_text = response.content.strip()
            return self.handle_success(summary_text)
        except Exception as exc:
            return self.handle_error(exc)


def build_summarizer_tool() -> StructuredTool:
    """构建摘要工具"""
    tool = SummarizerTool()
    
    return StructuredTool.from_function(
        func=tool.execute,
        name=tool.name,
        description=tool.description,
        args_schema=SummarizerInput,
        metadata={
            "output_key": "summarizer.result",
            "set_inputs_to_context": False,
            "input_keys": ["documents"],
        },
    )
