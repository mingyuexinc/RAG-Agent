from dataclasses import dataclass
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Literal

from config.app_config import AppConfig
from config.executor_config import TaskType, TASK_TOOL_CONSTRAINTS


class ExecutionResult(BaseModel):
    success: bool
    task_type: TaskType
    executed_tools: List[str]
    tool_results: Dict[str, Any]
    error: Optional[str] = None


class ExecutionContext:
    def __init__(self,max_size:int = 100):
        self.data = {}
        self.meta = {}
        self.max_size = max_size

    def set(self,key:str,value:Any):
        if len(self.data) >= self.max_size:
            self._cleanup()
        self.data[key] = value

    def get(self,key:str) -> Any:
        return self.data.get(key)

    def _cleanup(self):
        if len(self.data) > 0:
            oldest_key = next(iter(self.data))
            del self.data[oldest_key]

    def get_by_path(self, path: str):
        if path in self.data:
            return self.data[path]

        for output_key, value in self.data.items():
            if path.startswith(output_key + "."):
                sub_path = path[len(output_key) + 1:]
                return self._resolve_subpath(value, sub_path)

        return None

    def _resolve_subpath(self, value: Any, sub_path: str):
        parts = sub_path.split(".")
        current = value
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

@dataclass
class ExecutionPlan:
    task_type: TaskType
    need_tools: bool
    tools: List[str]
    tool_params: Dict[str, Dict[str, Any]]

    TASK_TOOL_CONSTRAINTS = AppConfig.executor.TASK_TOOL_CONSTRAINTS

    def validate(self, available_tools: List[str]):
        if self.task_type not in TASK_TOOL_CONSTRAINTS:
            raise ValueError(f"Unknown task_type: {self.task_type}")

        allowed_tools = TASK_TOOL_CONSTRAINTS[self.task_type]

        for tool in self.tools:
            if tool not in available_tools:
                raise ValueError(f"Unknown tool: {tool}")

            if tool not in allowed_tools:
                raise ValueError(
                    f"Tool {tool} not allowed for task_type {self.task_type}"
                )

        for tool in self.tools:
            if tool not in self.tool_params:
                raise ValueError(f"Missing params for tool: {tool}")