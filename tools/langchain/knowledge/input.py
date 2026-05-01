"""
知识检索工具输入模型
"""
from pydantic import BaseModel, Field


class KnowledgeSearchInput(BaseModel):
    """知识检索工具输入参数"""
    query: str = Field(
        ..., 
        min_length=1, 
        description="用户查询问题"
    )
