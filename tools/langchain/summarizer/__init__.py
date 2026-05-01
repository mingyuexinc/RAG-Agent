"""
摘要工具模块
"""
from .input import SummarizerInput
from .tool import build_summarizer_tool

__all__ = [
    "SummarizerInput",
    "build_summarizer_tool"
]
