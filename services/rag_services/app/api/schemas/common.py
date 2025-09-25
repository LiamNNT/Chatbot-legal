from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class SourceMeta(BaseModel):
    doc_id: str
    chunk_id: Optional[str] = None
    page: Optional[int] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

class CitationSpan(BaseModel):
    doc_id: str
    page: Optional[int] = None
    span: Optional[List[int]] = None  # [start, end] nếu có offset

class Pagination(BaseModel):
    offset: int = 0
    limit: int = 10