from agent.orchestrator.executor import ExecutionContext
from infra.config.app_config import AppConfig
from llm.model import ModelManager
from agent.prompts.prompt_manager import PromptManager
from agent.response.tool_result import ToolResult
from tools.base import BaseTool


class SummaryTool(BaseTool):
    name = "summarizer"
    input_keys = ["documents"]
    output_key = "summarizer.result"

    def __init__(self):
        super().__init__(name=self.name)
        self.prompt = PromptManager()

    def execute(self,context:ExecutionContext):
        try:
            documents = context.get("knowledge_search.result")
            documents = documents.get("documents")
            if not documents or not isinstance(documents, list):
                raise ValueError("No valid documents found in context")
            content = "\n".join([doc.get("content", "") for doc in documents])
            if not content:
                raise ValueError("No content found in documents")
            summarizer_prompt = self.prompt.render(
                AppConfig.prompt.TEMPLATE_SUMMARIZER,
                content=content,
                max_length=500
            )

            model_manager = ModelManager(timeout=30)
            response = model_manager.invoke_with_timeout(summarizer_prompt)
            summary_text = response.content.strip()

            result = ToolResult(
                success=True,
                data=summary_text
            )
            context.set(self.output_key, summary_text)
            return result.to_dict()
        except Exception as e:
            result = ToolResult(
                success=False,
                error=str(e),
                data=""
            )
            return result.to_dict()



