from typing import Optional, Dict, Any
from pydantic import BaseModel

from infra.config.executor_config import TaskType


class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    task_type:TaskType
    answer:Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    usage_metadata: Optional[list] = None

class UploadResponse(BaseModel):
    message:str
    filename:str
    file_id:str

class SearchResponse(BaseModel):
    query:str
    retrieved_documents:list
    similarity_score:list[float]