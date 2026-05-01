"""
工具注册中心
提供统一的工具注册、发现和实例化管理
"""
from dataclasses import dataclass, field
from typing import Dict, List, Type, Any, Callable
from functools import wraps

from .base import BaseLangChainTool


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    task_types: List[str]  # 该工具适用的任务类型
    dependencies: List[str]  # 依赖的资源名称
    tool_class: Type[BaseLangChainTool]  # 工具类
    description: str = ""
    builder_func: Callable = None  # 可选的构建器函数


class ToolRegistry:
    """
    工具注册中心 - 统一管理所有工具的注册、发现和实例化
    
    使用装饰器模式实现自动注册：
    @ToolRegistry.register(name="tool_name", task_types=["task1", "task2"])
    class MyTool(BaseLangChainTool):
        pass
    """
    
    # 存储所有已注册的工具元数据
    _tools: Dict[str, ToolMetadata] = {}
    
    # 任务类型到工具名称列表的映射
    _task_mappings: Dict[str, List[str]] = {}
    
    @classmethod
    def register(
        cls, 
        name: str, 
        task_types: List[str], 
        dependencies: List[str] = None,
        description: str = ""
    ):
        """
        装饰器：注册工具到注册中心
        
        Args:
            name: 工具唯一名称
            task_types: 该工具适用的任务类型列表
            dependencies: 工具依赖的资源列表 (如: ["vector_store"])
            description: 工具描述
        """
        def decorator(tool_class):
            # 注册工具元数据
            cls._tools[name] = ToolMetadata(
                name=name,
                task_types=task_types,
                dependencies=dependencies or [],
                tool_class=tool_class,
                description=description or getattr(tool_class, 'description', '')
            )
            
            # 自动建立任务映射关系
            for task_type in task_types:
                if task_type not in cls._task_mappings:
                    cls._task_mappings[task_type] = []
                if name not in cls._task_mappings[task_type]:
                    cls._task_mappings[task_type].append(name)
            
            # 设置工具类的类属性
            tool_class.name = name
            tool_class.task_types = task_types
            tool_class.dependencies = dependencies or []
            
            return tool_class
        return decorator
    
    @classmethod
    def register_builder(
        cls,
        name: str,
        task_types: List[str],
        dependencies: List[str] = None,
        description: str = ""
    ):
        """
        装饰器：注册工具构建器函数
        用于需要自定义构建逻辑的工具
        """
        def decorator(builder_func: Callable):
            cls._tools[name] = ToolMetadata(
                name=name,
                task_types=task_types,
                dependencies=dependencies or [],
                tool_class=None,  # 使用构建器时不需要类
                description=description,
                builder_func=builder_func
            )
            
            # 建立任务映射
            for task_type in task_types:
                if task_type not in cls._task_mappings:
                    cls._task_mappings[task_type] = []
                if name not in cls._task_mappings[task_type]:
                    cls._task_mappings[task_type].append(name)
            
            return builder_func
        return decorator
    
    @classmethod
    def get_tool(cls, name: str) -> ToolMetadata:
        """获取指定工具的元数据"""
        return cls._tools.get(name)
    
    @classmethod
    def get_tools_for_task(cls, task_type: str) -> List[str]:
        """获取指定任务类型可用的所有工具名称"""
        return cls._task_mappings.get(task_type, [])
    
    @classmethod
    def list_all_tools(cls) -> List[str]:
        """列出所有已注册的工具名称"""
        return list(cls._tools.keys())
    
    @classmethod
    def list_all_task_types(cls) -> List[str]:
        """列出所有已知的任务类型"""
        return list(cls._task_mappings.keys())
    
    @classmethod
    def build_tool(cls, name: str, **dependencies) -> Any:
        """
        构建并返回工具实例
        
        Args:
            name: 工具名称
            **dependencies: 工具依赖的资源，如 vector_store=vector_db
        """
        metadata = cls.get_tool(name)
        if not metadata:
            raise ValueError(f"Tool '{name}' not found in registry")
        
        # 使用构建器函数（如果存在）
        if metadata.builder_func:
            return metadata.builder_func(**dependencies)
        
        # 使用类构造器
        if metadata.tool_class:
            # 过滤出工具实际需要的依赖
            tool_deps = {}
            for dep_name in metadata.dependencies:
                if dep_name in dependencies:
                    tool_deps[dep_name] = dependencies[dep_name]
            
            return metadata.tool_class(**tool_deps)
        
        raise ValueError(f"Tool '{name}' has no builder function or class")
    
    @classmethod
    def build_tools_for_task(cls, task_type: str, **dependencies) -> Dict[str, Any]:
        """
        为指定任务类型构建所有需要的工具
        
        Args:
            task_type: 任务类型
            **dependencies: 依赖资源
            
        Returns:
            工具名称到工具实例的字典
        """
        tool_names = cls.get_tools_for_task(task_type)
        tools = {}
        for name in tool_names:
            tools[name] = cls.build_tool(name, **dependencies)
        return tools
    
    @classmethod
    def clear(cls):
        """清空注册中心 - 主要用于测试"""
        cls._tools.clear()
        cls._task_mappings.clear()
    
    @classmethod
    def debug_info(cls) -> Dict[str, Any]:
        """返回注册中心的调试信息"""
        return {
            "registered_tools": cls.list_all_tools(),
            "task_mappings": cls._task_mappings.copy(),
            "tool_count": len(cls._tools),
            "task_type_count": len(cls._task_mappings)
        }
