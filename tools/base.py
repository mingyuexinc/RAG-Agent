from abc import abstractmethod, ABC
from typing import List

from agent.orchestrator.executor import ExecutionContext
from agent.response.tool_result import ToolResult


class BaseTool(ABC):
    name:str
    input_keys:List[str]
    output_key:str

    def __init__(self,name:str):
        self.name = name

    def run(self,params:dict,context:ExecutionContext,set_input_to_context:bool):
        for key in self.input_keys:
            if key not in params:
                raise ValueError(f"Missing required param: {key}")
            if set_input_to_context:
                context.set(key,params[key])
        result = self.execute(context)
        if not isinstance(result,dict) or 'success' not in result:
            result = ToolResult(success=True,data=result).to_dict()
        return result


    @abstractmethod
    def execute(self,context:ExecutionContext):
        pass