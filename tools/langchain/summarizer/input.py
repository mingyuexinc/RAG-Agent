"""
摘要工具输入模型
"""
from typing import Any, Dict, List
from pydantic import BaseModel, Field


class SummarizerInput(BaseModel):
    """摘要工具输入参数"""
    documents: List[Dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="知识检索返回的文档列表",
    )
