"""
Schema definitions for Hybrid Two-Stage Knowledge Graph Extraction Pipeline.

This module contains all Pydantic models, enums, and configuration classes
used by the hybrid extractor for legal document processing.

Author: Legal Document Processing Team
Date: 2024
"""

from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


# =============================================================================
# Structural Extraction Models (Stage 1)
# =============================================================================

class StructureNodeType(str, Enum):
    """Types of structural nodes in legal documents."""
    DOCUMENT = "Document"
    CHAPTER = "Chapter"
    ARTICLE = "Article"
    CLAUSE = "Clause"
    POINT = "Point"
    TABLE = "Table"  # [NEW] Node loại Bảng


class StructureNode(BaseModel):
    """
    Structural node extracted from document pages (Stage 1).
    """
    id: str = Field(description="Unique ID (e.g., 'dieu_5', 'chuong_2', 'table_1_dieu_5')")
    type: StructureNodeType = Field(description="Type of structure node")
    title: str = Field(description="Title or heading (e.g., 'Điều 5', 'Bảng quy đổi')")
    full_text: str = Field(description="Complete text content. For Tables, this MUST be Markdown.")
    page_range: List[int] = Field(default_factory=list, description="Pages where this node appears")
    parent_id: Optional[str] = Field(default=None, description="ID of parent node")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StructureRelation(BaseModel):
    """Relation between structural nodes."""
    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    type: str = Field(default="CONTAINS", description="Relation type (CONTAINS, FOLLOWS)")


class StructureExtractionResult(BaseModel):
    """Result of Stage 1: Structural Extraction."""
    document: Optional[StructureNode] = Field(default=None)
    chapters: List[StructureNode] = Field(default_factory=list)
    articles: List[StructureNode] = Field(default_factory=list)
    clauses: List[StructureNode] = Field(default_factory=list)
    tables: List[StructureNode] = Field(default_factory=list)  # [NEW] Danh sách bảng riêng biệt
    relations: List[StructureRelation] = Field(default_factory=list)
    page_count: int = Field(default=0)
    errors: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# Semantic Extraction Models (Stage 2)
# =============================================================================

class SemanticNode(BaseModel):
    """Semantic entity extracted from text."""
    id: str = Field(description="Unique ID")
    type: str = Field(description="Entity type matching NodeCategory")
    text: str = Field(description="Entity text as appears in document")
    normalized: Optional[str] = Field(default=None, description="Normalized form")
    confidence: float = Field(default=0.9)
    source_article_id: str = Field(description="ID of the article this was extracted from")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticRelation(BaseModel):
    """Semantic relation between entities."""
    source_id: str = Field(description="Source entity ID")
    target_id: str = Field(description="Target entity ID")
    type: str = Field(description="Relation type matching RelationshipType")
    confidence: float = Field(default=0.9)
    evidence: str = Field(default="", description="Text evidence for this relation")
    source_article_id: str = Field(description="ID of the article this was extracted from")


class SemanticExtractionResult(BaseModel):
    """Result of Stage 2 for a single article."""
    article_id: str
    nodes: List[SemanticNode] = Field(default_factory=list)
    relations: List[SemanticRelation] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# Combined Result Models
# =============================================================================

class HybridExtractionResult(BaseModel):
    """Final result combining structure and semantics."""
    structure: StructureExtractionResult
    semantic_nodes: List[SemanticNode] = Field(default_factory=list)
    semantic_relations: List[SemanticRelation] = Field(default_factory=list)
    total_pages: int = Field(default=0)
    total_articles_processed: int = Field(default=0)
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class PageContext(BaseModel):
    """Context passed between pages."""
    current_chapter: Optional[str] = None
    current_chapter_id: Optional[str] = None
    current_article: Optional[str] = None
    current_article_id: Optional[str] = None
    current_clause: Optional[str] = None
    pending_text: Optional[str] = None
    pending_node_id: Optional[str] = None


# =============================================================================
# Configuration Models
# =============================================================================

class VLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


class VLMConfig(BaseModel):
    provider: VLMProvider = VLMProvider.OPENROUTER
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = 4096
    temperature: float = 0.0
    max_retries: int = 3
    retry_delay: float = 2.0

    @classmethod
    def from_env(cls, provider: VLMProvider = VLMProvider.OPENROUTER) -> "VLMConfig":
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        if provider == VLMProvider.OPENROUTER:
            api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
            model = os.getenv("VLM_MODEL", "openai/gpt-4o-mini")
            base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        elif provider == VLMProvider.OPENAI:
            api_key = os.getenv("OPENAI_API_KEY")
            model = os.getenv("VLM_MODEL", "gpt-4o")
            base_url = "https://api.openai.com/v1"
        elif provider == VLMProvider.GEMINI:
            api_key = os.getenv("GEMINI_API_KEY")
            model = os.getenv("VLM_MODEL", "gemini-1.5-flash")
            base_url = ""
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        if not api_key:
            raise ValueError(f"API key not found for {provider.value}.")
        return cls(provider=provider, api_key=api_key, model=model, base_url=base_url)


class LLMConfig(BaseModel):
    provider: str = "openrouter"
    api_key: Optional[str] = None
    model: str = "openai/gpt-4o-mini"
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = 2000
    temperature: float = 0.0
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
        base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        
        if not api_key:
            raise ValueError("API key not found for LLM.")
        return cls(api_key=api_key, model=model, base_url=base_url)


# =============================================================================
# Definitions & Prompts
# =============================================================================

VALID_ENTITY_TYPES = {
    "MON_HOC", "QUY_DINH", "DIEU_KIEN", "SINH_VIEN", "KHOA",
    "KY_HOC", "HOC_PHI", "DIEM_SO", "TIN_CHI", "THOI_GIAN",
    "NGANH", "CHUONG_TRINH_DAO_TAO", "GIANG_VIEN",
    "CHUNG_CHI", "DO_KHO", "DOI_TUONG", "TAI_CHINH", "DIEU_KIEN_SO"
}

VALID_RELATION_TYPES = {
    "YEU_CAU", "DIEU_KIEN_TIEN_QUYET", "AP_DUNG_CHO",
    "QUY_DINH_DIEU_KIEN", "THUOC_KHOA", "HOC_TRONG",
    "YEU_CAU_DIEU_KIEN", "LIEN_QUAN_NOI_DUNG", "CUA_NGANH",
    "THUOC_CHUONG_TRINH", "QUAN_LY",
    "DAT_DIEM", "TUONG_DUONG", "MIEN_GIAM", "CHI_PHOI", "THUOC_VE"
}

UNIFIED_ACADEMIC_SCHEMA = """
- **LOẠI THỰC THỂ (Entity Types):**
  + **MON_HOC**: Môn học (VD: "Anh văn 1", "ENG01").
  + **CHUNG_CHI**: Chứng chỉ (VD: "TOEIC", "IELTS").
  + **DIEM_SO**: Điểm số cụ thể (VD: "450", "5.0").
  + **DO_KHO**: Cấp độ/Trình độ (VD: "B1", "Bậc 3/6").
  + **DOI_TUONG**: Nhóm sinh viên (VD: "Chương trình tiên tiến", "Hệ CLC").
  + **QUY_DINH**: Tên văn bản (VD: "Điều 5").
  + **THOI_GIAN**: Thời hạn (VD: "đầu khóa", "2 năm").
  + **KHOA**: Đơn vị quản lý.
  + **NGANH**: Ngành học.

- **LOẠI QUAN HỆ (Relation Types):**
  + **DAT_DIEM**: (Chứng chỉ/Môn học) -> đạt mức -> (Điểm số).
  + **TUONG_DUONG**: (Thực thể A) -> tương đương -> (Thực thể B).
  + **MIEN_GIAM**: (Điều kiện) -> giúp miễn/giảm -> (Môn học).
  + **YEU_CAU**: (Môn học) -> yêu cầu bắt buộc -> (Điều kiện).
  + **AP_DUNG_CHO**: (Quy định) -> áp dụng cho -> (Đối tượng).
  + **QUY_DINH_DIEU_KIEN**: Điều chứa nội dung chi tiết.
"""

# [UPDATED] Structure Extraction Prompt - Dạy VLM nhận diện bảng không tiêu đề
STRUCTURE_EXTRACTION_PROMPT = """
You are an expert AI specializing in Vietnamese Legal Document Structure Extraction.
Your task is to analyze the provided document page and extract hierarchical structure into strict JSON.

## EXTRACTION RULES
1. **Chapter (Chương)**: Starts with "Chương" + Roman numerals.
2. **Article (Điều)**: Starts with "Điều" + Number (e.g., "Điều 1").
3. **Clause (Khoản)**: Number + dot (e.g., "1.").
4. **Table (Bảng)**: Any tabular data (lists of scores, courses).
   - **CRITICAL**: Convert table content strictly into **Markdown Table** format in `full_text`.
   - **SPLIT TABLES (QUAN TRỌNG)**: 
     - Check the top of the page. If you see table rows but **NO "Bảng X:" title/caption** above them, it is a continuation.
     - **ACTION**: Extract the content as Markdown, but leave the `title` field **EMPTY** (null) or set it to "Fragment".
     - **DO NOT** invent a title if one is not visually present.

## PROCESSING LOGIC
1. **Transcribe**: OCR/Read text strictly.
2. **Hierarchy**: Document > Chapter > Article > Clause > Table.
3. **Continuity**: Check `prev_context` to merge text.

## OUTPUT SCHEMA (JSON ONLY)
{{
  "nodes": [
    {{
      "id": "snake_case_id",
      "type": "Chapter" | "Article" | "Clause" | "Document" | "Table",
      "title": "Title (Leave empty if this is a split table fragment)",
      "full_text": "Content (Markdown for Tables)",
      "page_number": 1
    }}
  ],
  "relations": [
    {{ "source": "parent_id", "target": "child_id", "type": "CONTAINS" }}
  ],
  "next_context": {{ ... }}
}}
"""

SEMANTIC_EXTRACTION_PROMPT = """Bạn là chuyên gia xây dựng Knowledge Graph (KG).

## NHIỆM VỤ
Trích xuất Nodes (Thực thể) và Edges (Quan hệ) từ văn bản quy định.

## 1. SCHEMA
{schema_definition}

## 2. QUY TẮC XỬ LÝ (QUAN TRỌNG)
Văn bản đầu vào có thể chứa **Bảng Markdown** được nối vào cuối.
1. **Xử lý Bảng (Markdown Table):** - **BẮT BUỘC**: Phải đọc kỹ nội dung trong bảng Markdown.
   - Coi mỗi dòng trong bảng là một quy định.
   - Trích xuất quan hệ giữa các cột trong cùng dòng.
   - Ví dụ: Dòng `| TOEIC | 450 | Miễn AV1 |` -> `(TOEIC)--[DAT_DIEM]-->(450)--[MIEN_GIAM]-->(AV1)`.
2. **Quan hệ ngầm:** "IELTS 5.0" -> `(IELTS)--[DAT_DIEM]-->(5.0)`.
3. **ID Generation:** `{{article_id}}_ent_{{index}}`.

## INPUT
ID: {article_id}
Tiêu đề: {article_title}
Nội dung:
{article_text}

## OUTPUT FORMAT (JSON ONLY)
{{
  "entities": [
    {{"id": "1", "type": "MON_HOC", "text": "...", "normalized": "...", "confidence": 0.9}}
  ],
  "relations": [
    {{"source_id": "1", "target_id": "2", "type": "...", "evidence": "..."}}
  ]
}}
"""