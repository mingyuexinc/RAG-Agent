"""
流程图生成工具实现
使用装饰器自动注册到ToolRegistry
"""
from typing import Any, Dict

from langchain_core.tools import StructuredTool

from ..base import BaseLangChainTool
from ..registry import ToolRegistry
from ..utils.mermaid import generate_flowchart, generate_mermaid_image_url
from .input import ChartGenInput


@ToolRegistry.register(
    name="chart_gen",
    task_types=["flowchart_generation"],
    dependencies=[],  # chart_gen不需要外部依赖
    description="基于摘要文本生成流程图mermaid代码及图片URL"
)
class ChartGenTool(BaseLangChainTool):
    """流程图生成工具 - 自动注册"""
    
    name = "chart_gen"
    description = "基于摘要文本生成流程图mermaid代码及图片URL"
    task_types = ["flowchart_generation"]
    dependencies = []
    metadata = {
        "output_key": "flow_chart",
        "set_inputs_to_context": False,
        "input_keys": ["summarized_text"],
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def execute(self, summarized_text: str) -> Dict[str, Any]:
        """执行流程图生成"""
        try:
            chart_code = generate_flowchart(summarized_text)
            chart_url = generate_mermaid_image_url(chart_code)
            result_data = {
                "chart_code": chart_code,
                "chart_url": chart_url,
            }
            return self.handle_success(result_data)
        except Exception as exc:
            return self.handle_error(exc)


def build_chart_gen_tool() -> StructuredTool:
    """构建流程图生成工具"""
    tool = ChartGenTool()
    
    return StructuredTool.from_function(
        func=tool.execute,
        name=tool.name,
        description=tool.description,
        args_schema=ChartGenInput,
        metadata={
            "output_key": "flow_chart",
            "set_inputs_to_context": False,
            "input_keys": ["summarized_text"],
        },
    )
