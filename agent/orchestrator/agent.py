import uuid
from copy import deepcopy
from typing import Dict, Any, Optional

from agent.orchestrator.executor import ExecutionPlan, ExecutionResult, ExecutionContext
from agent.state.session_manager import SessionManager
from agent.state.state_manager import AgentStateManager
from infra.config.app_config import AppConfig

from llm.model import ModelManager
from tools.base import BaseTool


class DocAgent:
    def __init__(self,tools:Dict[str,BaseTool]):
        self.tools = tools
        self.max_steps = AppConfig.agent.MAX_STEPS
        self.max_retries = AppConfig.agent.MAX_RETRIES
        self.max_content_size = AppConfig.agent.MAX_CONTENT_SIZE

        self.session_manager = SessionManager()
        self.state_manager = AgentStateManager()

    def ensure_session(self, session_id: Optional[str]) -> str:
        # first request
        if not session_id:
            session_id = str(uuid.uuid4())
            self.session_manager.create_session(session_id)
            self.state_manager.init(session_id)
            return session_id

        session = self.session_manager.get_session(session_id)
        if session is None:  # expired
            self.session_manager.create_session(session_id)
            self.state_manager.init(session_id)

        return session_id

    def execute_with_session(self, plan:ExecutionPlan,session_id:str)-> ExecutionResult:

        state = self.state_manager.load(session_id)
        if state is None:
            raise RuntimeError(
                f"State not initialized for session_id={session_id}"
            )

        executed_tools = []
        tool_results = {}
        step_count = 0

        try:
            for tool_name in plan.tools:
                if step_count >= self.max_steps:
                    raise ValueError("Exceeded maximum execution steps: {self.max_step}")

                state_snapshot = {
                    "executed_tools": executed_tools.copy(),
                    "tool_results": deepcopy(tool_results),
                    "context": deepcopy(state.working_context)
                }

                retry_count = 0
                success = False

                while retry_count < self.max_retries and not success:
                    try:
                        if tool_name not in self.tools:
                            raise ValueError(f"Unknown tool: {tool_name}")
                        tool = self.tools[tool_name]

                        raw_params = plan.tool_params.get(tool_name, {})
                        resolved_params = self._resolve_params(raw_params, state.working_context)
                        if tool_name == "knowledge_search":
                            set_tool = True
                        else:
                            set_tool = False
                        result = tool.run(resolved_params, state.working_context, set_tool)

                        executed_tools.append(tool_name)
                        tool_results[tool_name] = result

                        state.last_tool_results = tool_results
                        success = result.get("success")
                    except Exception as e:
                        retry_count += 1
                        if retry_count >= self.max_retries:
                            raise ValueError(f"Failed to execute tool: {tool_name} after {self.max_retries} retries: {str(e)}")
                        else:
                            executed_tools = state_snapshot["executed_tools"].copy()
                            tool_results = state_snapshot["tool_results"].deepcopy()
                            state.working_context = state_snapshot["context"].deepcopy()
                step_count += 1

            return ExecutionResult(
                success = True,
                task_type=plan.task_type,
                executed_tools = executed_tools,
                tool_results = tool_results,
            )

        except Exception as e:
            return ExecutionResult(
                success = False,
                task_type=plan.task_type,
                executed_tools = executed_tools,
                tool_results = tool_results,
                error = str(e)
            )

    def _resolve_params(self,params:Dict[str,Any],context:ExecutionContext) -> Dict[str,Any]:
        resolved = {}
        for key,value in params.items():
            if isinstance(value, str) and "." in value:
                resolved_value = context.get_by_path(value)
                if resolved_value is None:
                    raise ValueError(f"Missing dependency: {value}")
                resolved[key] = resolved_value

            else:
                resolved[key] = value
        return resolved


    def generate_response(self, prompt:str) -> str:
        model_manager = ModelManager(timeout=30)
        response = model_manager.invoke_with_timeout(prompt)
        return response.content.strip()





