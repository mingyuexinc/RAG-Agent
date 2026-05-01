import unittest

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.orchestrator.agent import DocAgent
from agent.orchestrator.executor import ExecutionPlan
from agent.response.tool_result import ToolResult


class QueryInput(BaseModel):
    query: str = Field(..., min_length=1)


class DocsInput(BaseModel):
    documents: list = Field(..., min_length=1)


class SummaryInput(BaseModel):
    summarized_text: str = Field(..., min_length=1)


class DocAgentLangChainToolTests(unittest.TestCase):
    def _build_agent(self):
        def search(query: str):
            docs = {"documents": [{"content": f"doc about {query}", "metadata": {}, "score": 0.9}]}
            return ToolResult(success=True, data=docs).to_dict()

        def summarize(documents: list):
            joined = "\n".join([doc.get("content", "") for doc in documents]).strip()
            return ToolResult(success=True, data=f"summary:{joined}").to_dict()

        def chart_gen(summarized_text: str):
            return ToolResult(
                success=True,
                data={"chart_code": f"graph TD\nA[{summarized_text}]", "chart_url": "https://mermaid.ink/img/mock"},
            ).to_dict()

        tools = {
            "knowledge_search": StructuredTool.from_function(
                func=search,
                name="knowledge_search",
                description="search tool",
                args_schema=QueryInput,
                metadata={
                    "output_key": "knowledge_search.result",
                    "set_inputs_to_context": True,
                    "input_keys": ["query"],
                },
            ),
            "summarizer": StructuredTool.from_function(
                func=summarize,
                name="summarizer",
                description="summary tool",
                args_schema=DocsInput,
                metadata={
                    "output_key": "summarizer.result",
                    "set_inputs_to_context": False,
                    "input_keys": ["documents"],
                },
            ),
            "chart_gen": StructuredTool.from_function(
                func=chart_gen,
                name="chart_gen",
                description="chart tool",
                args_schema=SummaryInput,
                metadata={
                    "output_key": "flow_chart",
                    "set_inputs_to_context": False,
                    "input_keys": ["summarized_text"],
                },
            ),
        }
        agent = DocAgent(tools)
        agent.max_retries = 1
        return agent

    def test_execute_keeps_plan_order_and_writes_context(self):
        agent = self._build_agent()
        session_id = agent.ensure_session(None)

        plan = ExecutionPlan(
            task_type="flowchart_generation",
            need_tools=True,
            tools=["knowledge_search", "summarizer", "chart_gen"],
            tool_params={
                "knowledge_search": {"query": "python"},
                "summarizer": {"documents": "knowledge_search.result.documents"},
                "chart_gen": {"summarized_text": "summarizer.result"},
            },
        )

        result = agent.execute_with_session(plan, session_id)
        self.assertTrue(result.success)
        self.assertEqual(result.executed_tools, ["knowledge_search", "summarizer", "chart_gen"])

        state = agent.state_manager.load(session_id)
        self.assertEqual(state.working_context.get("query"), "python")
        self.assertIsNotNone(state.working_context.get("knowledge_search.result"))
        self.assertIsNotNone(state.working_context.get("summarizer.result"))
        self.assertIsNotNone(state.working_context.get("flow_chart"))

    def test_execute_fails_when_dependency_missing(self):
        agent = self._build_agent()
        session_id = agent.ensure_session(None)

        plan = ExecutionPlan(
            task_type="summary",
            need_tools=True,
            tools=["summarizer"],
            tool_params={"summarizer": {"documents": "knowledge_search.result.documents"}},
        )

        result = agent.execute_with_session(plan, session_id)
        self.assertFalse(result.success)
        self.assertIn("Missing dependency", result.error)

    def test_execute_fails_on_schema_validation(self):
        agent = self._build_agent()
        session_id = agent.ensure_session(None)

        plan = ExecutionPlan(
            task_type="summary",
            need_tools=True,
            tools=["summarizer"],
            tool_params={"summarizer": {"documents": "not_a_list"}},
        )

        result = agent.execute_with_session(plan, session_id)
        self.assertFalse(result.success)
        self.assertIn("Failed to execute tool: summarizer", result.error)


if __name__ == "__main__":
    unittest.main()
