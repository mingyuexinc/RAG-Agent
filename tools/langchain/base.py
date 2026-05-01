"""
LangChain工具基础类
提供统一的工具基类和通用功能，支持自描述和依赖注入
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, ClassVar

from agent.response.tool_result import ToolResult
from infra.logs.logger_config import get_logger

logger = get_logger("tools.base")


class BaseLangChainTool(ABC):
    """
    LangChain工具基础类
    
    支持自描述能力：
    - name: 工具名称（类属性）
    - description: 工具描述（类属性）
    - task_types: 适用任务类型（类属性）
    - dependencies: 依赖列表（类属性）
    """
    
    # 类属性 - 用于自描述
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    task_types: ClassVar[List[str]] = []
    dependencies: ClassVar[List[str]] = []
    metadata: ClassVar[Dict[str, Any]] = {}
    
    def __init__(self, **kwargs):
        """
        支持动态依赖注入
        
        Args:
            **kwargs: 依赖资源，如 vector_store=vector_db
        """
        self.logger = get_logger(f"tools.{self.name or 'unknown'}")
        
        # 动态注入依赖
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具逻辑"""
        pass

    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """Keep custom tools compatible with the executor's LangChain-style calls."""
        if input is None:
            input = {}
        if not isinstance(input, dict):
            raise TypeError(f"Tool input must be a dict, got {type(input).__name__}")
        return self.execute(**input)
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """统一错误处理"""
        self.logger.error(f"{self.name} failed: {error}", exc_info=True)
        return ToolResult(
            success=False,
            error=str(error),
            data={}
        ).to_dict()
    
    def handle_success(self, data: Any) -> Dict[str, Any]:
        """统一成功处理"""
        return ToolResult(success=True, data=data).to_dict()
