from typing import Optional

from pydantic import BaseModel, Field


class DocumentParserInput(BaseModel):
    """Input schema for document_parser."""

    file_path: str = Field(..., min_length=1, description="Local document path")
    filename: Optional[str] = Field(None, description="Original uploaded filename")
    page_ranges: Optional[str] = Field(
        None,
        description="Optional page range expression, for example '1-3,5'",
    )
    ocr_language: Optional[str] = Field(
        None,
        description="Optional OCR language hint, for example 'ch' or 'en'",
    )
    parse_mode: Optional[str] = Field(
        "auto",
        description="Parser mode hint, for example 'auto', 'ocr', or 'txt'",
    )
