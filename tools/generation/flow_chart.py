from typing import Dict, Any

from agent.orchestrator.executor import ExecutionContext
from tools.base import BaseTool
from agent.response.tool_result import ToolResult

import base64

class ChartGenTool(BaseTool):
    name = "chart_gen"
    input_keys = ["summarized_text"]
    output_key = "flow_chart"

    def __init__(self):
        super().__init__(name=self.name)

    def execute(self,context:ExecutionContext) -> Dict[str, Any]:
        try:
            summarized_text = context.get("summarizer.result")

            chart_code = self._generate_flowchart(summarized_text)
            chart_url = self._generate_mermaid_image_url(chart_code)

            result_data = {
                "chart_code":chart_code,
                "chart_url":chart_url
            }

            result = ToolResult(
                success=True,
                data=result_data
            )
            context.set(self.output_key, result_data)
            return result.to_dict()
        except Exception as e:
            result = ToolResult(
                success=False,
                error=str(e),
                data = {"chart_code":"", "chart_url":""}
            )
            return result.to_dict()

    def _generate_flowchart(self, content: str) -> str:

        lines = [line.strip() for line in content.split('\n') if line.strip()]

        nodes = [line[:60] + "..." if len(line) > 60 else line for line in lines[:15]]

        mermaid_code = "graph TD\n"

        for i, node in enumerate(nodes):
            node_id = chr(65 + i)  # A, B, C...

            clean_node = node.replace('"', '').replace("'", "")
            mermaid_code += f"    {node_id}[{clean_node}]\n"

            if i > 0:
                prev_node_id = chr(65 + i - 1)
                mermaid_code += f"    {prev_node_id} --> {node_id}\n"

        return mermaid_code

    def _generate_mermaid_image_url(self, mermaid_code: str) -> str:
        try:
            encoded = base64.urlsafe_b64encode(
                mermaid_code.encode("utf-8")
            ).decode("utf-8").rstrip("=")
            return f"https://mermaid.ink/img/{encoded}"

        except Exception as e:
            raise ValueError(f"Failed to generate Mermaid image: {str(e)}")