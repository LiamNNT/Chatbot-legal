from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class SearchMode(Enum):
    VECTOR = "vector"
    BM25 = "bm25"
    HYBRID = "hybrid"


class DocumentLanguage(Enum):
    VIETNAMESE = "vi"
    ENGLISH = "en"

@dataclass
class CharacterSpan:
    start: int
    end: int
    text: str
    type: str = "content"


@dataclass
class DocumentMetadata:
    doc_id: str
    chunk_id: Optional[str] = None
    title: Optional[str] = None
    page: Optional[int] = None
    doc_type: Optional[str] = None   
    faculty: Optional[str] = None 
    year: Optional[int] = None
    subject: Optional[str] = None
    language: DocumentLanguage = DocumentLanguage.VIETNAMESE
    section: Optional[str] = None
    subsection: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchFilters:
    doc_types: Optional[List[str]] = None
    faculties: Optional[List[str]] = None
    years: Optional[List[int]] = None
    subjects: Optional[List[str]] = None
    language: Optional[DocumentLanguage] = None
    metadata_filters: Optional[Dict[str, Any]] = None


@dataclass
class RerankingMetadata:
    original_rank: int
    original_score: float
    rerank_score: float
    confidence: Optional[float] = None
    model_name: Optional[str] = None
    processing_time_ms: Optional[int] = None

@dataclass
class SearchQuery:
    text: str
    top_k: int = 8
    search_mode: SearchMode = SearchMode.HYBRID
    use_rerank: bool = True
    bm25_weight: Optional[float] = None
    vector_weight: Optional[float] = None
    filters: Optional[SearchFilters] = None
    include_char_spans: bool = True
    highlight_matches: bool = True


@dataclass
class SearchResult:
    text: str
    metadata: DocumentMetadata
    score: float
    source_type: str  # "vector" | "bm25" | "fused"
    rank: Optional[int] = None
    char_spans: Optional[List[CharacterSpan]] = None
    highlighted_text: Optional[List[str]] = None
    highlighted_title: Optional[List[str]] = None
    bm25_score: Optional[float] = None
    vector_score: Optional[float] = None
    rerank_score: Optional[float] = None
    reranking_metadata: Optional[RerankingMetadata] = None


@dataclass
class SearchResponse:
    results: List[SearchResult]
    total_hits: int
    latency_ms: int
    facets: Optional[Dict[str, List[Dict[str, Any]]]] = None
    search_metadata: Optional[Dict[str, Any]] = None

@dataclass
class Document:
    text: str
    metadata: DocumentMetadata


@dataclass
class DocumentChunk:
    text: str
    metadata: DocumentMetadata
    chunk_index: int
    char_spans: Optional[List[CharacterSpan]] = None
    embedding: Optional[List[float]] = None
