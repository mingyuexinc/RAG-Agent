from typing import Any, Dict

from pydantic import BaseModel, Field


class KnowledgeSearchInput(BaseModel):
    """Input schema for the vector retrieval tool."""

    query: str = Field(..., min_length=1, description="User query")
    top_k: int = Field(
        5,
        ge=1,
        le=20,
        description="Number of retrieved chunks to return",
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata filters such as file_id, document_type, title, or block_type",
    )
