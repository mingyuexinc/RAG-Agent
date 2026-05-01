"""
知识检索工具模块
"""
from .input import KnowledgeSearchInput
from .tool import build_knowledge_search_tool

__all__ = [
    "KnowledgeSearchInput",
    "build_knowledge_search_tool"
]
