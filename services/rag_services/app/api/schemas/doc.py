from pydantic import BaseModel
from typing import Optional, Dict, Any

class ManifestSpec(BaseModel):
    source_dir: Optional[str] = None
    glob: str = "**/*"
    metadata: Dict[str, Any] = {}
    chunk_size: int = 512
    chunk_overlap: int = 64

class ReindexResponse(BaseModel):
    status: str
    indexed_docs: int
