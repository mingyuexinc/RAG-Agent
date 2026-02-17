import json
import re

from config.app_config import AppConfig
from prompts.prompt_manager import PromptManager
from .executor import ExecutionPlan
from model import ModelManager
from .session.state_manager import AgentState


class TaskPlanner:
    def __init__(self):
        self.prompt_manager = PromptManager()

    def analyze_task(self, query: str,state: AgentState):
        state_view = state.to_prompt_view("planner")

        prompt = self.prompt_manager.render(
           "templates/planner_template.txt",
           query=query,
           **state_view,
           task_schema=AppConfig.executor.JSON_TASK_SCHEMA,
        )

        model_manager = ModelManager(timeout=30)
        response = model_manager.invoke_with_timeout(prompt)
        parsed_plan = self.parse_plan(response.content)
        return parsed_plan

    def parse_plan(self, response: str) -> ExecutionPlan:

        if not response:
            raise ValueError("Empty plan response")
        cleaned = re.sub(r"```json|```", "", response).strip()
        raw = json.loads(cleaned)
        # parse
        plan = ExecutionPlan(
            task_type=raw.get("task_type"),
            need_tools=raw.get("need_tools", False),
            tools=raw.get("tools", []),
            tool_params=raw.get("tool_params", {}),
        )
        # validate
        plan.validate(available_tools=["knowledge_search", "summarizer", "chart_gen"])
        return plan