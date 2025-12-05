"""
Hybrid Two-Stage Knowledge Graph Extraction Pipeline for Legal Documents.

This module implements a two-stage extraction pipeline:
    - Stage 1 (Structural Extraction): Uses VLM to extract document structure
      (Document, Chapter, Article) from page images with OCR and cross-page text merging.
    - Stage 2 (Semantic Extraction): Uses LLM to extract semantic entities
      (e.g., MonHoc, DiemSo) and relations (YEU_CAU, DIEU_KIEN) from article text.

The output maps to Pydantic models defined in core.domain.graph_models.

Author: Legal Document Processing Team
Date: 2024
"""

import asyncio
import base64
import json
import logging
import sys
import time
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import utility modules for robust JSON parsing and cross-page merging
from scripts.json_utils import clean_and_parse_json
from scripts.page_merger import merge_nodes_into_dict

from pydantic import BaseModel, Field

# Import domain models
from core.domain.graph_models import (
    GraphNode,
    GraphRelationship,
    NodeCategory,
    RelationshipType,
    Entity,
    Relation,
    SubGraph,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Two-Stage Pipeline
# =============================================================================

class StructureNodeType(str, Enum):
    """Types of structural nodes in legal documents."""
    DOCUMENT = "Document"
    CHAPTER = "Chapter"
    ARTICLE = "Article"
    CLAUSE = "Clause"
    POINT = "Point"


class SemanticNodeType(str, Enum):
    """Types of semantic nodes extracted from article content."""
    ENTITY = "Entity"
    SUBJECT = "Subject"
    CONDITION = "Condition"
    ACTION = "Action"
    SANCTION = "Sanction"
    REFERENCE = "Reference"
    DEFINITION = "Definition"


class StructureNode(BaseModel):
    """
    Structural node extracted from document pages (Stage 1).
    
    Represents document structure: Document -> Chapter -> Article -> Clause.
    """
    id: str = Field(description="Unique ID (e.g., 'dieu_5', 'chuong_2')")
    type: StructureNodeType = Field(description="Type of structure node")
    title: str = Field(description="Title or heading (e.g., 'Điều 5. Quy định về học phí')")
    full_text: str = Field(description="Complete text content including merged cross-page text")
    page_range: List[int] = Field(default_factory=list, description="Pages where this node appears")
    parent_id: Optional[str] = Field(default=None, description="ID of parent node (Chapter for Article, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StructureRelation(BaseModel):
    """Relation between structural nodes."""
    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    type: str = Field(default="CONTAINS", description="Relation type (CONTAINS, FOLLOWS)")


class StructureExtractionResult(BaseModel):
    """Result of Stage 1: Structural Extraction."""
    document: Optional[StructureNode] = Field(default=None, description="Document node")
    chapters: List[StructureNode] = Field(default_factory=list)
    articles: List[StructureNode] = Field(default_factory=list)
    clauses: List[StructureNode] = Field(default_factory=list)
    relations: List[StructureRelation] = Field(default_factory=list)
    page_count: int = Field(default=0)
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class SemanticNode(BaseModel):
    """
    Semantic node extracted from article text (Stage 2).
    
    Represents entities like: MonHoc, DiemSo, SinhVien, etc.
    """
    id: str = Field(description="Unique ID")
    type: str = Field(description="Entity type matching NodeCategory")
    text: str = Field(description="Entity text as appears in document")
    normalized: Optional[str] = Field(default=None, description="Normalized form")
    confidence: float = Field(default=0.9)
    source_article_id: str = Field(description="ID of the article this was extracted from")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticRelation(BaseModel):
    """Semantic relation extracted from article text (Stage 2)."""
    source_id: str = Field(description="Source entity ID")
    target_id: str = Field(description="Target entity ID")
    type: str = Field(description="Relation type matching RelationshipType")
    confidence: float = Field(default=0.9)
    evidence: str = Field(default="", description="Text evidence for this relation")
    source_article_id: str = Field(description="ID of the article this was extracted from")


class SemanticExtractionResult(BaseModel):
    """Result of Stage 2: Semantic Extraction for one article."""
    article_id: str
    nodes: List[SemanticNode] = Field(default_factory=list)
    relations: List[SemanticRelation] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class HybridExtractionResult(BaseModel):
    """
    Final result combining both stages.
    
    Contains both structural and semantic information ready for graph storage.
    """
    # Stage 1 results
    structure: StructureExtractionResult
    
    # Stage 2 results (aggregated from all articles)
    semantic_nodes: List[SemanticNode] = Field(default_factory=list)
    semantic_relations: List[SemanticRelation] = Field(default_factory=list)
    
    # Combined stats
    total_pages: int = Field(default=0)
    total_articles_processed: int = Field(default=0)
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class PageContext(BaseModel):
    """Context state passed between pages during structural extraction."""
    current_chapter: Optional[str] = None
    current_chapter_id: Optional[str] = None
    current_article: Optional[str] = None
    current_article_id: Optional[str] = None
    current_clause: Optional[str] = None
    pending_text: Optional[str] = None
    pending_node_id: Optional[str] = None


# =============================================================================
# VLM Configuration (Reused from vlm_recursive_extractor.py)
# =============================================================================

class VLMProvider(str, Enum):
    """Supported VLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


class VLMConfig(BaseModel):
    """Configuration for VLM API calls."""
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
        """Load configuration from environment variables."""
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        if provider == VLMProvider.OPENROUTER:
            # Try multiple env var names for API key
            api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
            model = os.getenv("VLM_MODEL", "openai/gpt-4.1")
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
            raise ValueError(f"API key not found for {provider.value}. Set OPENROUTER_API_KEY or OPENAI_API_KEY.")
        
        logger.info(f"VLM Config loaded: provider={provider.value}, model={model}, base_url={base_url[:30]}...")
        
        return cls(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url
        )


class LLMConfig(BaseModel):
    """Configuration for LLM API calls (Stage 2)."""
    provider: str = "openrouter"
    api_key: Optional[str] = None
    model: str = "openai/gpt-4o-mini"
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = 2000
    temperature: float = 0.1
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load configuration from environment variables."""
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
        base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        
        if not api_key:
            raise ValueError("API key not found. Set OPENROUTER_API_KEY or OPENAI_API_KEY")
        
        logger.info(f"LLM Config loaded: model={model}")
        
        return cls(api_key=api_key, model=model, base_url=base_url)


# =============================================================================
# Stage 1: Structure Extractor (VLM)
# =============================================================================

STRUCTURE_EXTRACTION_PROMPT = """Bạn là chuyên gia phân tích cấu trúc văn bản quy phạm pháp luật Việt Nam.

## NHIỆM VỤ
Từ ảnh trang văn bản pháp luật, hãy:
1. OCR toàn bộ nội dung
2. Nhận diện và trích xuất cấu trúc: Document, Chapter (Chương), Article (Điều), Clause (Khoản)
3. Xử lý văn bản bị ngắt trang (nối pending_text từ trang trước)

## CONTEXT TỪ TRANG TRƯỚC
{prev_context}

## HƯỚNG DẪN TRÍCH XUẤT

### Trích xuất Structural Nodes
Với mỗi Điều/Khoản/Chương trong văn bản, tạo một node với:
- `id`: ID duy nhất, format snake_case (VD: "dieu_1", "khoan_3_dieu_4")
- `type`: "Document", "Chapter", "Article", "Clause", "Point"
- `title`: Tiêu đề ngắn gọn
- `full_text`: Toàn bộ nội dung văn bản của node đó
- `page_number`: Số trang

### Trích xuất Relations
- "CONTAINS": Quyết định chứa Điều, Điều chứa Khoản
- "FOLLOWS": Điều 2 theo sau Điều 1

### Cập nhật Context cho trang sau
- `pending_text`: Nếu văn bản bị cắt giữa chừng, lưu phần cuối
- `pending_node_id`: ID của node chứa pending_text

## YÊU CẦU OUTPUT
QUAN TRỌNG: CHỈ trả về JSON object, KHÔNG có markdown, KHÔNG có giải thích.

Trả về ĐÚNG format JSON sau:
{{"nodes": [{{"id": "dieu_1", "type": "Article", "title": "Điều 1. ...", "full_text": "...", "page_number": 1}}], "relations": [{{"source": "quyet_dinh", "target": "dieu_1", "type": "CONTAINS"}}], "next_context": {{"current_chapter": null, "current_chapter_id": null, "current_article": "Điều 1", "current_article_id": "dieu_1", "current_clause": null, "pending_text": null, "pending_node_id": null}}}}"""


class StructureExtractor:
    """
    Stage 1: Structural Extraction using VLM.
    
    Extracts document structure (Document, Chapter, Article, Clause)
    from page images using Vision Language Models.
    
    Features:
    - OCR with cross-page text merging
    - Hierarchical structure recognition
    - Context propagation between pages
    
    Example:
        ```python
        config = VLMConfig.from_env()
        extractor = StructureExtractor(config)
        
        result = extractor.extract_from_images(["page1.png", "page2.png"])
        
        for article in result.articles:
            print(f"{article.title}: {len(article.full_text)} chars")
        ```
    """
    
    def __init__(self, config: VLMConfig):
        """
        Initialize the structure extractor.
        
        Args:
            config: VLM configuration
        """
        self.config = config
        logger.info(f"StructureExtractor initialized with {config.provider.value}/{config.model}")
    
    def _encode_image(self, image_path: Path) -> Tuple[str, str]:
        """Encode image to base64 and get media type."""
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        extension = image_path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(extension, "image/png")
        
        return image_base64, media_type
    
    def _call_vlm_api(
        self,
        image_base64: str,
        media_type: str,
        prev_context: PageContext,
        page_number: int
    ) -> str:
        """Call VLM API to extract structure from image."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Install: pip install openai")
        
        prompt = STRUCTURE_EXTRACTION_PROMPT.format(
            prev_context=prev_context.model_dump_json(indent=2)
        )
        
        user_content = [
            {
                "type": "text",
                "text": f"Đây là trang {page_number} của văn bản pháp luật.\n\n{prompt}"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_base64}",
                    "detail": "high"
                }
            }
        ]
        
        if self.config.provider == VLMProvider.GEMINI:
            # Use Gemini API directly
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            model = genai.GenerativeModel(self.config.model)
            
            image_bytes = base64.b64decode(image_base64)
            response = model.generate_content([
                prompt,
                {"mime_type": media_type, "data": image_bytes}
            ])
            return response.text
        else:
            # Use OpenAI-compatible API (OpenAI or OpenRouter)
            client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url if self.config.base_url else None
            )
            
            extra_headers = {}
            if self.config.provider == VLMProvider.OPENROUTER:
                extra_headers = {
                    "HTTP-Referer": "https://github.com/LiamNNT/Chatbot-UIT",
                    "X-Title": "Legal Document KG Extractor"
                }
            
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": user_content}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                extra_headers=extra_headers if extra_headers else None
            )
            
            result = response.choices[0].message.content
            logger.debug(f"VLM API response (page {page_number}): {result[:500] if result else 'None'}...")
            
            if not result:
                raise ValueError("Empty response from VLM API")
            
            return result
    
    def _parse_vlm_response(self, response_text: str, page_number: int) -> Dict[str, Any]:
        """Parse VLM response JSON using robust JSON cleaning."""
        if not response_text:
            logger.error(f"Empty response for page {page_number}")
            return {"nodes": [], "relations": [], "next_context": {}}
        
        logger.debug(f"Raw VLM response for page {page_number}:\n{response_text[:1000]}")
        
        # Use robust JSON parser from json_utils
        data, errors = clean_and_parse_json(response_text, logger)
        
        if errors:
            for err in errors:
                logger.warning(f"JSON parsing issue on page {page_number}: {err}")
        
        if data is None:
            logger.error(f"Failed to parse VLM response for page {page_number}")
            return {"nodes": [], "relations": [], "next_context": {}}
        
        # Ensure expected keys exist
        if not isinstance(data, dict):
            logger.error(f"VLM response is not a dict for page {page_number}: {type(data)}")
            return {"nodes": [], "relations": [], "next_context": {}}
        
        logger.debug(f"Parsed JSON successfully for page {page_number}")
        return data
    
    def _process_single_page(
        self,
        image_path: Path,
        prev_context: PageContext,
        page_number: int
    ) -> Tuple[List[StructureNode], List[StructureRelation], PageContext]:
        """Process a single page image."""
        logger.info(f"Processing page {page_number}: {image_path.name}")
        
        image_base64, media_type = self._encode_image(image_path)
        logger.debug(f"Image encoded: {len(image_base64)} chars, type: {media_type}")
        
        last_error = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                logger.debug(f"Calling VLM API for page {page_number}, attempt {attempt}")
                response_text = self._call_vlm_api(
                    image_base64, media_type, prev_context, page_number
                )
                
                logger.debug(f"VLM response received: {len(response_text) if response_text else 0} chars")
                
                data = self._parse_vlm_response(response_text, page_number)
                
                # Check if we got valid data
                if not data.get("nodes") and not data.get("relations"):
                    logger.warning(f"Empty extraction result for page {page_number}")
                
                # Parse nodes
                nodes = []
                for node_data in data.get("nodes", []):
                    try:
                        node = StructureNode(
                            id=node_data["id"],
                            type=StructureNodeType(node_data["type"]),
                            title=node_data.get("title", ""),
                            full_text=node_data.get("full_text", ""),
                            page_range=[node_data.get("page_number", page_number)],
                            metadata={"source_page": page_number}
                        )
                        nodes.append(node)
                    except Exception as e:
                        logger.warning(f"Failed to parse node: {node_data}, error: {e}")
                
                # Parse relations
                relations = []
                for rel_data in data.get("relations", []):
                    try:
                        rel = StructureRelation(
                            source=rel_data["source"],
                            target=rel_data["target"],
                            type=rel_data.get("type", "CONTAINS")
                        )
                        relations.append(rel)
                    except Exception as e:
                        logger.warning(f"Failed to parse relation: {rel_data}, error: {e}")
                
                # Parse next context
                next_ctx_data = data.get("next_context", {})
                next_context = PageContext(
                    current_chapter=next_ctx_data.get("current_chapter"),
                    current_chapter_id=next_ctx_data.get("current_chapter_id"),
                    current_article=next_ctx_data.get("current_article"),
                    current_article_id=next_ctx_data.get("current_article_id"),
                    current_clause=next_ctx_data.get("current_clause"),
                    pending_text=next_ctx_data.get("pending_text"),
                    pending_node_id=next_ctx_data.get("pending_node_id")
                )
                
                logger.info(f"Page {page_number}: {len(nodes)} nodes, {len(relations)} relations")
                return nodes, relations, next_context
                
            except Exception as e:
                last_error = e
                import traceback
                logger.warning(f"Page {page_number}, attempt {attempt} failed: {type(e).__name__}: {e}")
                logger.debug(f"Traceback:\n{traceback.format_exc()}")
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay)
        
        logger.error(f"Failed to process page {page_number}: {last_error}")
        return [], [], prev_context
    
    def _merge_cross_page_nodes(
        self,
        all_nodes: List[StructureNode],
        pending_texts: Dict[str, List[Tuple[int, str]]]
    ) -> List[StructureNode]:
        """Merge text from nodes that span multiple pages."""
        nodes_by_id = {n.id: n for n in all_nodes}
        
        for node_id, page_texts in pending_texts.items():
            if node_id in nodes_by_id:
                node = nodes_by_id[node_id]
                for page_num, text in page_texts:
                    if text not in node.full_text:
                        node.full_text = node.full_text.rstrip() + " " + text.lstrip()
                    if page_num not in node.page_range:
                        node.page_range.append(page_num)
                node.page_range.sort()
        
        return list(nodes_by_id.values())
    
    def _find_real_parent(
        self,
        clause_node: StructureNode,
        all_nodes: List[StructureNode],
        valid_node_ids: set
    ) -> Optional[str]:
        """
        Find the real parent Article for a Clause node.
        
        For amendment documents (văn bản sửa đổi), a clause like "Khoản 2 Điều 12"
        physically appears inside "Điều 1" but references "Điều 12" which doesn't exist.
        This method finds the actual containing Article.
        
        Logic:
        1. Look for the Article on the same page with smallest page number >= clause's page
        2. If not found, find the Article that appears just before this clause
        
        Args:
            clause_node: The clause needing a parent
            all_nodes: All extracted nodes
            valid_node_ids: Set of valid node IDs
            
        Returns:
            ID of the real parent Article, or None if not found
        """
        clause_page = min(clause_node.page_range) if clause_node.page_range else 0
        
        # Get all valid Articles
        articles = [
            n for n in all_nodes 
            if n.type == StructureNodeType.ARTICLE and n.id in valid_node_ids
        ]
        
        if not articles:
            # No articles, try to find Document
            for n in all_nodes:
                if n.type == StructureNodeType.DOCUMENT and n.id in valid_node_ids:
                    return n.id
            return None
        
        # Strategy 1: Find Article on same page or earlier page
        candidates = []
        for article in articles:
            article_page = min(article.page_range) if article.page_range else 0
            if article_page <= clause_page:
                candidates.append((article_page, article.id))
        
        if candidates:
            # Sort by page (descending) to get the nearest Article before/on the clause
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
        
        # Strategy 2: Just return the first Article if all else fails
        return articles[0].id if articles else None
    
    def extract_from_images(
        self,
        image_paths: List[Path],
        continue_on_error: bool = True
    ) -> StructureExtractionResult:
        """
        Extract document structure from page images.
        
        Uses intelligent cross-page merging to handle nodes spanning multiple pages.
        
        Args:
            image_paths: List of paths to page images (sorted by page order)
            continue_on_error: Continue processing if a page fails
            
        Returns:
            StructureExtractionResult with document structure
        """
        logger.info(f"Starting structural extraction from {len(image_paths)} pages")
        
        # Use dict for intelligent merging: node_id -> StructureNode
        merged_nodes: Dict[str, StructureNode] = {}
        all_relations: List[StructureRelation] = []
        errors: List[Dict[str, Any]] = []
        
        current_context = PageContext()
        
        for page_num, image_path in enumerate(image_paths, start=1):
            try:
                nodes, relations, next_context = self._process_single_page(
                    Path(image_path), current_context, page_num
                )
                
                # Use merge_nodes_into_dict for intelligent cross-page merging
                # This APPENDs text for same IDs instead of overwriting
                merged_nodes = merge_nodes_into_dict(merged_nodes, nodes, page_num, logger)
                
                all_relations.extend(relations)
                
                current_context = next_context
                
            except Exception as e:
                errors.append({
                    "page_number": page_num,
                    "error": str(e)
                })
                logger.error(f"Error on page {page_num}: {e}")
                if not continue_on_error:
                    raise
        
        # Convert merged dict to list
        all_nodes = list(merged_nodes.values())
        
        # =====================================================================
        # FIX GHOST PARENTS: Validate and repair relations
        # =====================================================================
        valid_node_ids = {node.id for node in all_nodes}
        valid_relations = []
        ghost_parent_fixes = []
        
        for rel in all_relations:
            source_exists = rel.source in valid_node_ids
            target_exists = rel.target in valid_node_ids
            
            if source_exists and target_exists:
                # Both nodes exist - relation is valid
                valid_relations.append(rel)
            elif not source_exists and target_exists and rel.type == "CONTAINS":
                # Ghost parent case: source doesn't exist
                # Find the real parent (nearest Article above in document order)
                target_node = merged_nodes.get(rel.target)
                if target_node and target_node.type in [StructureNodeType.CLAUSE, StructureNodeType.POINT]:
                    # Find the article that actually contains this clause
                    real_parent_id = self._find_real_parent(
                        target_node, all_nodes, valid_node_ids
                    )
                    if real_parent_id:
                        fixed_rel = StructureRelation(
                            source=real_parent_id,
                            target=rel.target,
                            type="CONTAINS"
                        )
                        valid_relations.append(fixed_rel)
                        ghost_parent_fixes.append({
                            "original_source": rel.source,
                            "fixed_source": real_parent_id,
                            "target": rel.target
                        })
                        logger.info(f"Fixed ghost parent: {rel.source} -> {real_parent_id} for {rel.target}")
            elif source_exists and not target_exists:
                # Target doesn't exist - skip this relation
                logger.warning(f"Skipping relation with missing target: {rel.source} -> {rel.target}")
            else:
                # Both don't exist - skip
                logger.warning(f"Skipping relation with missing nodes: {rel.source} -> {rel.target}")
        
        # Deduplicate relations
        seen_relations = set()
        deduplicated_relations = []
        for rel in valid_relations:
            rel_key = (rel.source, rel.target, rel.type)
            if rel_key not in seen_relations:
                seen_relations.add(rel_key)
                deduplicated_relations.append(rel)
        
        all_relations = deduplicated_relations
        
        if ghost_parent_fixes:
            logger.info(f"Fixed {len(ghost_parent_fixes)} ghost parent relations")
        
        # Categorize nodes
        document = None
        chapters = []
        articles = []
        clauses = []
        
        for node in all_nodes:
            if node.type == StructureNodeType.DOCUMENT:
                document = node
            elif node.type == StructureNodeType.CHAPTER:
                chapters.append(node)
            elif node.type == StructureNodeType.ARTICLE:
                articles.append(node)
            elif node.type in [StructureNodeType.CLAUSE, StructureNodeType.POINT]:
                clauses.append(node)
        
        result = StructureExtractionResult(
            document=document,
            chapters=chapters,
            articles=articles,
            clauses=clauses,
            relations=all_relations,
            page_count=len(image_paths),
            errors=errors
        )
        
        logger.info(
            f"Structural extraction complete: "
            f"{len(chapters)} chapters, {len(articles)} articles, {len(clauses)} clauses"
        )
        
        return result
    
    def extract_from_pdf(
        self,
        pdf_path: Path,
        output_dir: Optional[Path] = None,
        dpi: int = 200,
        keep_images: bool = True
    ) -> StructureExtractionResult:
        """
        Extract structure from a PDF file.
        
        Converts PDF to images first, then extracts structure.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save images
            dpi: Resolution for PDF rendering
            keep_images: Keep images after processing
            
        Returns:
            StructureExtractionResult
        """
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError(
                "pdf2image required. Install: pip install pdf2image\n"
                "Also install poppler for your OS."
            )
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        if output_dir is None:
            output_dir = pdf_path.parent / f"{pdf_path.stem}_images"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting PDF to images: {pdf_path}")
        images = convert_from_path(pdf_path, dpi=dpi, fmt="png")
        
        image_paths = []
        for i, image in enumerate(images, start=1):
            filename = f"page_{str(i).zfill(3)}.png"
            image_path = output_dir / filename
            image.save(image_path, "PNG")
            image_paths.append(image_path)
        
        logger.info(f"Converted {len(images)} pages")
        
        result = self.extract_from_images(image_paths)
        
        if not keep_images:
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
        
        return result


# =============================================================================
# Stage 2: Semantic Extractor (LLM)
# =============================================================================

SEMANTIC_EXTRACTION_PROMPT = """Bạn là chuyên gia trích xuất thực thể và quan hệ từ văn bản quy định học vụ.

## NHIỆM VỤ
Từ nội dung Điều luật sau, trích xuất:
1. **Entities (Thực thể)**: Các đối tượng được đề cập
2. **Relations (Quan hệ)**: Mối liên hệ giữa các thực thể

## LOẠI THỰC THỂ (theo CatRAG Schema)
- MON_HOC: Môn học, học phần (VD: "IT001", "Nhập môn lập trình")
- QUY_DINH: Quy định, điều khoản
- DIEU_KIEN: Điều kiện (VD: "tối thiểu 70 sinh viên", "đạt 4.0 điểm")
- SINH_VIEN: Sinh viên, người học
- KHOA: Khoa, đơn vị (VD: "Khoa CNTT", "P.ĐTĐH")
- KY_HOC: Kỳ học (VD: "học kỳ hè", "học kỳ chính")
- HOC_PHI: Học phí, chi phí
- DIEM_SO: Điểm số, thang điểm
- TIN_CHI: Số tín chỉ
- THOI_GIAN: Thời gian, thời hạn

## LOẠI QUAN HỆ (theo CatRAG Schema)
- YEU_CAU: Yêu cầu điều kiện
- DIEU_KIEN_TIEN_QUYET: Môn học tiên quyết (chỉ MON_HOC -> MON_HOC)
- AP_DUNG_CHO: Quy định áp dụng cho đối tượng
- QUY_DINH_DIEU_KIEN: Quy định về điều kiện
- THUOC_KHOA: Thuộc khoa/đơn vị
- HOC_TRONG: Học trong kỳ học

## INPUT
Điều: {article_id}
Tiêu đề: {article_title}
Nội dung:
{article_text}

## OUTPUT FORMAT
Trả về JSON với cấu trúc:
- "entities": mảng các thực thể, mỗi thực thể có id, type, text, normalized, confidence
- "relations": mảng các quan hệ, mỗi quan hệ có source_id, target_id, type, confidence, evidence

CHỈ trả về JSON hợp lệ, không có text giải thích."""


class SemanticExtractor:
    """
    Stage 2: Semantic Extraction using LLM.
    
    Extracts entities (MonHoc, DiemSo, etc.) and relations (YEU_CAU, DIEU_KIEN)
    from article text using Large Language Models.
    
    Features:
    - CatRAG schema-guided extraction
    - Confidence scoring
    - Evidence tracking
    
    Example:
        ```python
        config = LLMConfig.from_env()
        extractor = SemanticExtractor(config)
        
        result = extractor.extract_from_article(
            article_id="dieu_5",
            article_title="Điều 5. Về học phí",
            article_text="Học phí = HPTCHM..."
        )
        
        for entity in result.nodes:
            print(f"{entity.type}: {entity.text}")
        ```
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize the semantic extractor.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        logger.info(f"SemanticExtractor initialized with {config.model}")
    
    def _call_llm_api(self, prompt: str) -> str:
        """Call LLM API for semantic extraction."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Install: pip install openai")
        
        client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url if self.config.base_url else None
        )
        
        response = client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )
        
        return response.choices[0].message.content
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response JSON using robust parser."""
        from scripts.json_utils import clean_and_parse_json
        
        if not response_text:
            logger.warning("Empty LLM response")
            return {"entities": [], "relations": []}
        
        # Use robust JSON parser
        data, errors = clean_and_parse_json(response_text, logger)
        
        if errors:
            for err in errors:
                logger.warning(f"JSON parsing issue: {err}")
        
        if data is None:
            logger.error(f"Failed to parse LLM response, raw text: {response_text[:500]}")
            return {"entities": [], "relations": []}
        
        # Ensure expected structure
        if not isinstance(data, dict):
            logger.error(f"LLM response is not a dict: {type(data)}")
            return {"entities": [], "relations": []}
        
        # Ensure keys exist
        if "entities" not in data:
            data["entities"] = []
        if "relations" not in data:
            data["relations"] = []
        
        return data
    
    def _post_process_extraction(
        self, 
        data: Dict[str, Any], 
        parent_article_id: str
    ) -> Dict[str, Any]:
        """
        Post-process LLM extraction result to fix common issues.
        
        Fixes:
        1. Convert int IDs to string (Pydantic validation)
        2. Globalize IDs to ensure uniqueness across articles
           Format: {parent_article_id}_ent_{original_id}
        
        Args:
            data: Raw parsed JSON from LLM
            parent_article_id: The article ID this extraction belongs to
            
        Returns:
            Processed data with fixed IDs
        """
        # Build ID mapping: old_id -> new_global_id
        id_mapping = {}
        
        # Process entities
        processed_entities = []
        for ent in data.get("entities", []):
            old_id = ent.get("id")
            
            # Convert to string and create global ID
            old_id_str = str(old_id) if old_id is not None else "unknown"
            new_id = f"{parent_article_id}_ent_{old_id_str}"
            
            # Store mapping
            id_mapping[old_id_str] = new_id
            # Also map int version if it was int
            if isinstance(old_id, int):
                id_mapping[old_id] = new_id
            
            # Create processed entity
            processed_ent = {**ent, "id": new_id}
            processed_entities.append(processed_ent)
        
        # Process relations with updated IDs
        processed_relations = []
        for rel in data.get("relations", []):
            source_id = rel.get("source_id")
            target_id = rel.get("target_id")
            
            # Convert to string first
            source_id_str = str(source_id) if source_id is not None else "unknown"
            target_id_str = str(target_id) if target_id is not None else "unknown"
            
            # Map to global IDs
            new_source = id_mapping.get(source_id, id_mapping.get(source_id_str, f"{parent_article_id}_ent_{source_id_str}"))
            new_target = id_mapping.get(target_id, id_mapping.get(target_id_str, f"{parent_article_id}_ent_{target_id_str}"))
            
            # Create processed relation
            processed_rel = {
                **rel,
                "source_id": new_source,
                "target_id": new_target
            }
            processed_relations.append(processed_rel)
        
        logger.debug(
            f"Post-processed {parent_article_id}: "
            f"{len(processed_entities)} entities, {len(processed_relations)} relations, "
            f"ID mappings: {len(id_mapping)}"
        )
        
        return {
            "entities": processed_entities,
            "relations": processed_relations
        }
    
    def _validate_entity_type(self, entity_type: str) -> bool:
        """Validate entity type against CatRAG schema."""
        valid_types = {
            "MON_HOC", "QUY_DINH", "DIEU_KIEN", "SINH_VIEN", "KHOA",
            "KY_HOC", "HOC_PHI", "DIEM_SO", "TIN_CHI", "THOI_GIAN",
            "NGANH", "CHUONG_TRINH_DAO_TAO", "GIANG_VIEN"
        }
        return entity_type.upper() in valid_types
    
    def _validate_relation_type(self, rel_type: str) -> bool:
        """Validate relation type against CatRAG schema."""
        valid_types = {
            "YEU_CAU", "DIEU_KIEN_TIEN_QUYET", "AP_DUNG_CHO",
            "QUY_DINH_DIEU_KIEN", "THUOC_KHOA", "HOC_TRONG",
            "YEU_CAU_DIEU_KIEN", "LIEN_QUAN_NOI_DUNG", "CUA_NGANH",
            "THUOC_CHUONG_TRINH", "QUAN_LY"
        }
        return rel_type.upper() in valid_types
    
    def extract_from_article(
        self,
        article_id: str,
        article_title: str,
        article_text: str
    ) -> SemanticExtractionResult:
        """
        Extract semantic entities and relations from a single article.
        
        Args:
            article_id: Article ID (e.g., "dieu_5")
            article_title: Article title
            article_text: Full text content of the article
            
        Returns:
            SemanticExtractionResult with extracted entities and relations
        """
        logger.info(f"Extracting semantics from article: {article_id}")
        
        prompt = SEMANTIC_EXTRACTION_PROMPT.format(
            article_id=article_id,
            article_title=article_title,
            article_text=article_text
        )
        
        errors = []
        
        try:
            response_text = self._call_llm_api(prompt)
            raw_data = self._parse_llm_response(response_text)
            
            # Post-process: fix int IDs and globalize IDs
            data = self._post_process_extraction(raw_data, article_id)
            
            # Parse entities
            nodes = []
            for ent_data in data.get("entities", []):
                try:
                    entity_type = ent_data.get("type", "").upper()
                    if not self._validate_entity_type(entity_type):
                        logger.warning(f"Invalid entity type: {entity_type}")
                        continue
                    
                    node = SemanticNode(
                        id=ent_data["id"],  # Now guaranteed to be string
                        type=entity_type,
                        text=ent_data.get("text", ""),
                        normalized=ent_data.get("normalized"),
                        confidence=float(ent_data.get("confidence", 0.9)),
                        source_article_id=article_id,
                        metadata={"article_title": article_title}
                    )
                    nodes.append(node)
                except Exception as e:
                    errors.append(f"Failed to parse entity: {e}")
            
            # Parse relations
            relations = []
            for rel_data in data.get("relations", []):
                try:
                    rel_type = rel_data.get("type", "").upper()
                    if not self._validate_relation_type(rel_type):
                        logger.warning(f"Invalid relation type: {rel_type}")
                        continue
                    
                    relation = SemanticRelation(
                        source_id=rel_data["source_id"],  # Now guaranteed to be string
                        target_id=rel_data["target_id"],  # Now guaranteed to be string
                        type=rel_type,
                        confidence=float(rel_data.get("confidence", 0.9)),
                        evidence=rel_data.get("evidence", ""),
                        source_article_id=article_id
                    )
                    relations.append(relation)
                except Exception as e:
                    errors.append(f"Failed to parse relation: {e}")
            
            logger.info(f"Article {article_id}: {len(nodes)} entities, {len(relations)} relations")
            
            return SemanticExtractionResult(
                article_id=article_id,
                nodes=nodes,
                relations=relations,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Semantic extraction failed for {article_id}: {e}")
            return SemanticExtractionResult(
                article_id=article_id,
                nodes=[],
                relations=[],
                errors=[str(e)]
            )
    
    def extract_from_articles(
        self,
        articles: List[StructureNode],
        continue_on_error: bool = True
    ) -> List[SemanticExtractionResult]:
        """
        Extract semantics from multiple articles.
        
        Args:
            articles: List of article nodes from Stage 1
            continue_on_error: Continue if one article fails
            
        Returns:
            List of SemanticExtractionResult for each article
        """
        results = []
        
        for article in articles:
            try:
                result = self.extract_from_article(
                    article_id=article.id,
                    article_title=article.title,
                    article_text=article.full_text
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to extract from article {article.id}: {e}")
                if not continue_on_error:
                    raise
                results.append(SemanticExtractionResult(
                    article_id=article.id,
                    errors=[str(e)]
                ))
        
        return results


# =============================================================================
# Parallel Semantic Extractor (Optimized Stage 2)
# =============================================================================

class ParallelSemanticExtractor:
    """
    Stage 2: Parallel Semantic Extraction using async LLM calls.
    
    Optimized version of SemanticExtractor that processes multiple articles
    concurrently using asyncio, with rate limiting and error handling.
    
    Features:
    - Concurrent processing with configurable concurrency limit (Semaphore)
    - Automatic retry with exponential backoff
    - Progress bar with tqdm
    - Graceful error handling (one failure doesn't crash everything)
    
    Example:
        ```python
        config = LLMConfig.from_env()
        extractor = ParallelSemanticExtractor(config, max_concurrency=5)
        
        # Async usage
        results = await extractor.extract_batch_async(articles)
        
        # Sync wrapper
        results = extractor.extract_batch(articles)
        ```
    """
    
    def __init__(
        self, 
        config: LLMConfig, 
        max_concurrency: int = 5,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize parallel semantic extractor.
        
        Args:
            config: LLM configuration
            max_concurrency: Maximum concurrent API calls (default: 5)
            max_retries: Maximum retry attempts for failed calls (default: 3)
            retry_delay: Base delay between retries in seconds (default: 1.0)
        """
        self.config = config
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._semaphore: Optional[asyncio.Semaphore] = None
        
        # Create sync extractor for reusing parsing logic
        self._sync_extractor = SemanticExtractor(config)
        
        logger.info(
            f"ParallelSemanticExtractor initialized: "
            f"model={config.model}, concurrency={max_concurrency}"
        )
    
    async def _call_llm_async(self, prompt: str) -> str:
        """
        Call LLM API asynchronously using OpenAI's async client.
        
        Returns:
            Response text from LLM
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package required. Install: pip install openai")
        
        client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url if self.config.base_url else None
        )
        
        response = await client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )
        
        return response.choices[0].message.content
    
    async def _extract_single_async(
        self,
        article_id: str,
        article_title: str,
        article_text: str,
        pbar: Optional[Any] = None
    ) -> SemanticExtractionResult:
        """
        Extract semantics from a single article with retries.
        
        Args:
            article_id: Article ID
            article_title: Article title  
            article_text: Article content
            pbar: Optional tqdm progress bar
            
        Returns:
            SemanticExtractionResult
        """
        prompt = SEMANTIC_EXTRACTION_PROMPT.format(
            article_id=article_id,
            article_title=article_title,
            article_text=article_text
        )
        
        errors = []
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Acquire semaphore to limit concurrency
                async with self._semaphore:
                    response_text = await self._call_llm_async(prompt)
                
                # Parse response (reuse sync extractor's logic)
                raw_data = self._sync_extractor._parse_llm_response(response_text)
                data = self._sync_extractor._post_process_extraction(raw_data, article_id)
                
                # Parse entities
                nodes = []
                for ent_data in data.get("entities", []):
                    try:
                        entity_type = ent_data.get("type", "").upper()
                        if not self._sync_extractor._validate_entity_type(entity_type):
                            continue
                        
                        node = SemanticNode(
                            id=ent_data["id"],
                            type=entity_type,
                            text=ent_data.get("text", ""),
                            normalized=ent_data.get("normalized"),
                            confidence=float(ent_data.get("confidence", 0.9)),
                            source_article_id=article_id,
                            metadata={"article_title": article_title}
                        )
                        nodes.append(node)
                    except Exception as e:
                        errors.append(f"Entity parse error: {e}")
                
                # Parse relations
                relations = []
                for rel_data in data.get("relations", []):
                    try:
                        rel_type = rel_data.get("type", "").upper()
                        if not self._sync_extractor._validate_relation_type(rel_type):
                            continue
                        
                        relation = SemanticRelation(
                            source_id=rel_data["source_id"],
                            target_id=rel_data["target_id"],
                            type=rel_type,
                            confidence=float(rel_data.get("confidence", 0.9)),
                            evidence=rel_data.get("evidence", ""),
                            source_article_id=article_id
                        )
                        relations.append(relation)
                    except Exception as e:
                        errors.append(f"Relation parse error: {e}")
                
                logger.info(f"Article {article_id}: {len(nodes)} entities, {len(relations)} relations")
                
                if pbar:
                    pbar.update(1)
                
                return SemanticExtractionResult(
                    article_id=article_id,
                    nodes=nodes,
                    relations=relations,
                    errors=errors
                )
                
            except Exception as e:
                last_error = e
                wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                
                # Check if rate limit error
                error_str = str(e).lower()
                if "429" in error_str or "rate" in error_str:
                    wait_time = wait_time * 2  # Double wait for rate limits
                    logger.warning(
                        f"Rate limit hit for {article_id}, "
                        f"retry {attempt + 1}/{self.max_retries} in {wait_time:.1f}s"
                    )
                else:
                    logger.warning(
                        f"Error extracting {article_id}: {e}, "
                        f"retry {attempt + 1}/{self.max_retries} in {wait_time:.1f}s"
                    )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        logger.error(f"Failed to extract {article_id} after {self.max_retries} attempts: {last_error}")
        
        if pbar:
            pbar.update(1)
        
        return SemanticExtractionResult(
            article_id=article_id,
            nodes=[],
            relations=[],
            errors=[f"Failed after {self.max_retries} retries: {last_error}"]
        )
    
    async def extract_batch_async(
        self,
        articles: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> List[SemanticExtractionResult]:
        """
        Extract semantics from multiple articles concurrently.
        
        Args:
            articles: List of article dicts with 'id', 'title', 'full_text'
            show_progress: Whether to show tqdm progress bar
            
        Returns:
            List of SemanticExtractionResult
        """
        if not articles:
            return []
        
        # Initialize semaphore
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        
        # Setup progress bar
        pbar = None
        if show_progress:
            try:
                from tqdm.asyncio import tqdm
                pbar = tqdm(total=len(articles), desc="Semantic Extraction", unit="article")
            except ImportError:
                logger.warning("tqdm not installed, progress bar disabled")
        
        # Create tasks
        tasks = []
        for article in articles:
            article_id = article.get("id", "")
            article_title = article.get("title", "")
            article_text = article.get("full_text", "")
            
            task = self._extract_single_async(
                article_id=article_id,
                article_title=article_title,
                article_text=article_text,
                pbar=pbar
            )
            tasks.append(task)
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Close progress bar
        if pbar:
            pbar.close()
        
        # Process results (handle any exceptions)
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                article_id = articles[i].get("id", f"unknown_{i}")
                logger.error(f"Task exception for {article_id}: {result}")
                processed_results.append(SemanticExtractionResult(
                    article_id=article_id,
                    nodes=[],
                    relations=[],
                    errors=[str(result)]
                ))
            else:
                processed_results.append(result)
        
        # Log summary
        total_entities = sum(len(r.nodes) for r in processed_results)
        total_relations = sum(len(r.relations) for r in processed_results)
        total_errors = sum(len(r.errors) for r in processed_results)
        
        logger.info(
            f"Parallel extraction complete: {len(articles)} articles, "
            f"{total_entities} entities, {total_relations} relations, "
            f"{total_errors} errors"
        )
        
        return processed_results
    
    def extract_batch(
        self,
        articles: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> List[SemanticExtractionResult]:
        """
        Synchronous wrapper for extract_batch_async.
        
        Args:
            articles: List of article dicts with 'id', 'title', 'full_text'
            show_progress: Whether to show tqdm progress bar
            
        Returns:
            List of SemanticExtractionResult
        """
        return asyncio.run(self.extract_batch_async(articles, show_progress))
    
    def extract_from_structure(
        self,
        structure_result: StructureExtractionResult,
        show_progress: bool = True
    ) -> List[SemanticExtractionResult]:
        """
        Extract semantics from Stage 1 structure result.
        
        Args:
            structure_result: Result from StructureExtractor
            show_progress: Whether to show progress bar
            
        Returns:
            List of SemanticExtractionResult
        """
        # Convert StructureNode to dict format
        articles = []
        for article in structure_result.articles:
            articles.append({
                "id": article.id,
                "title": article.title,
                "full_text": article.full_text
            })
        
        return self.extract_batch(articles, show_progress)


# =============================================================================
# Pipeline: Combining Both Stages
# =============================================================================

def convert_to_graph_models(
    hybrid_result: HybridExtractionResult
) -> Tuple[List[GraphNode], List[GraphRelationship]]:
    """
    Convert HybridExtractionResult to core domain models (GraphNode, GraphRelationship).
    
    Maps the extraction result to Pydantic models in core.domain.graph_models.
    
    Args:
        hybrid_result: Result from the hybrid extraction pipeline
        
    Returns:
        Tuple of (list of GraphNode, list of GraphRelationship)
    """
    graph_nodes = []
    graph_relationships = []
    
    # Convert structural nodes to GraphNode
    structure = hybrid_result.structure
    
    # Map structure node types to NodeCategory
    def get_node_category(struct_type: StructureNodeType) -> Optional[NodeCategory]:
        # Structural nodes don't directly map to CatRAG categories
        # They form the document hierarchy
        return None  # Will be stored with different labels
    
    # Convert articles to a special node type (can be extended)
    for article in structure.articles:
        # Articles are converted as QUY_DINH nodes
        try:
            properties = {
                "id": article.id,
                "title": article.title,
                "year": 2024,  # Default year, can be extracted from document
                "full_text": article.full_text,
                "page_range": article.page_range,
                "source": "legal_document"
            }
            node = GraphNode(
                id=article.id,
                category=NodeCategory.QUY_DINH,
                properties=properties
            )
            graph_nodes.append(node)
        except Exception as e:
            logger.warning(f"Failed to convert article {article.id}: {e}")
    
    # Convert semantic nodes to GraphNode
    for sem_node in hybrid_result.semantic_nodes:
        try:
            # Map semantic types to NodeCategory
            type_mapping = {
                "MON_HOC": NodeCategory.MON_HOC,
                "QUY_DINH": NodeCategory.QUY_DINH,
                "DIEU_KIEN": NodeCategory.DIEU_KIEN,
                "SINH_VIEN": NodeCategory.SINH_VIEN,
                "KHOA": NodeCategory.KHOA,
                "KY_HOC": NodeCategory.KY_HOC,
                "HOC_PHI": NodeCategory.HOC_PHI,
                "NGANH": NodeCategory.NGANH,
                "CHUONG_TRINH_DAO_TAO": NodeCategory.CHUONG_TRINH_DAO_TAO,
                "GIANG_VIEN": NodeCategory.GIANG_VIEN,
            }
            
            category = type_mapping.get(sem_node.type)
            if not category:
                logger.warning(f"Unknown semantic type: {sem_node.type}")
                continue
            
            # Build properties based on category requirements
            properties = {
                "text": sem_node.text,
                "normalized": sem_node.normalized,
                "confidence": sem_node.confidence,
                "source_article": sem_node.source_article_id,
            }
            
            # Add required properties for each category
            if category == NodeCategory.MON_HOC:
                properties.update({
                    "code": sem_node.id,
                    "name": sem_node.normalized or sem_node.text,
                    "credits": 0  # Default, needs extraction
                })
            elif category == NodeCategory.QUY_DINH:
                properties.update({
                    "id": sem_node.id,
                    "title": sem_node.text,
                    "year": 2024
                })
            elif category == NodeCategory.DIEU_KIEN:
                properties.update({
                    "id": sem_node.id,
                    "type": "general",
                    "description": sem_node.text
                })
            elif category == NodeCategory.KHOA:
                properties.update({
                    "code": sem_node.id,
                    "name": sem_node.text
                })
            elif category == NodeCategory.KY_HOC:
                properties.update({
                    "code": sem_node.id,
                    "year": 2024
                })
            elif category == NodeCategory.SINH_VIEN:
                properties.update({
                    "cohort": "general"
                })
            
            node = GraphNode(
                id=sem_node.id,
                category=category,
                properties=properties
            )
            graph_nodes.append(node)
            
        except Exception as e:
            logger.warning(f"Failed to convert semantic node {sem_node.id}: {e}")
    
    # Convert semantic relations to GraphRelationship
    for sem_rel in hybrid_result.semantic_relations:
        try:
            # Map relation types to RelationshipType
            type_mapping = {
                "YEU_CAU": RelationshipType.YEU_CAU_DIEU_KIEN,
                "DIEU_KIEN_TIEN_QUYET": RelationshipType.DIEU_KIEN_TIEN_QUYET,
                "AP_DUNG_CHO": RelationshipType.AP_DUNG_CHO,
                "QUY_DINH_DIEU_KIEN": RelationshipType.QUY_DINH_DIEU_KIEN,
                "THUOC_KHOA": RelationshipType.THUOC_KHOA,
                "HOC_TRONG": RelationshipType.HOC_TRONG,
                "YEU_CAU_DIEU_KIEN": RelationshipType.YEU_CAU_DIEU_KIEN,
                "LIEN_QUAN_NOI_DUNG": RelationshipType.LIEN_QUAN_NOI_DUNG,
                "CUA_NGANH": RelationshipType.CUA_NGANH,
                "THUOC_CHUONG_TRINH": RelationshipType.THUOC_CHUONG_TRINH,
                "QUAN_LY": RelationshipType.QUAN_LY,
            }
            
            rel_type = type_mapping.get(sem_rel.type)
            if not rel_type:
                logger.warning(f"Unknown relation type: {sem_rel.type}")
                continue
            
            relationship = GraphRelationship(
                source_id=sem_rel.source_id,
                target_id=sem_rel.target_id,
                rel_type=rel_type,
                properties={
                    "confidence": sem_rel.confidence,
                    "evidence": sem_rel.evidence,
                    "source_article": sem_rel.source_article_id
                }
            )
            graph_relationships.append(relationship)
            
        except Exception as e:
            logger.warning(f"Failed to convert relation: {e}")
    
    return graph_nodes, graph_relationships


def run_pipeline(
    image_paths: Optional[List[Path]] = None,
    pdf_path: Optional[Path] = None,
    vlm_config: Optional[VLMConfig] = None,
    llm_config: Optional[LLMConfig] = None,
    output_path: Optional[Path] = None,
    continue_on_error: bool = True
) -> Tuple[HybridExtractionResult, List[GraphNode], List[GraphRelationship]]:
    """
    Run the complete two-stage extraction pipeline.
    
    Pipeline:
        Images/PDF -> Stage 1 (VLM Structure) -> List[Article]
                   -> Stage 2 (LLM Semantic per Article) -> Full Knowledge Graph
    
    Args:
        image_paths: List of page image paths (mutually exclusive with pdf_path)
        pdf_path: Path to PDF file (mutually exclusive with image_paths)
        vlm_config: VLM configuration for Stage 1 (default: from env)
        llm_config: LLM configuration for Stage 2 (default: from env)
        output_path: Optional path to save JSON result
        continue_on_error: Continue processing on errors
        
    Returns:
        Tuple of:
            - HybridExtractionResult: Raw extraction result
            - List[GraphNode]: Nodes mapped to graph_models.py
            - List[GraphRelationship]: Relations mapped to graph_models.py
    
    Example:
        ```python
        # From images
        result, nodes, rels = run_pipeline(
            image_paths=[Path("page1.png"), Path("page2.png")]
        )
        
        # From PDF
        result, nodes, rels = run_pipeline(pdf_path=Path("document.pdf"))
        
        print(f"Extracted {len(nodes)} nodes, {len(rels)} relationships")
        ```
    """
    if not image_paths and not pdf_path:
        raise ValueError("Either image_paths or pdf_path must be provided")
    
    # Load configs from environment if not provided
    if vlm_config is None:
        vlm_config = VLMConfig.from_env()
    if llm_config is None:
        llm_config = LLMConfig.from_env()
    
    logger.info("=" * 60)
    logger.info("HYBRID TWO-STAGE EXTRACTION PIPELINE")
    logger.info("=" * 60)
    
    # =========================================================================
    # Stage 1: Structural Extraction
    # =========================================================================
    logger.info("\n[STAGE 1] Structural Extraction with VLM")
    logger.info("-" * 40)
    
    structure_extractor = StructureExtractor(vlm_config)
    
    if pdf_path:
        structure_result = structure_extractor.extract_from_pdf(
            Path(pdf_path),
            keep_images=True
        )
    else:
        structure_result = structure_extractor.extract_from_images(
            [Path(p) for p in image_paths],
            continue_on_error=continue_on_error
        )
    
    logger.info(f"Stage 1 complete: {len(structure_result.articles)} articles extracted")
    
    # =========================================================================
    # Stage 2: Semantic Extraction
    # =========================================================================
    logger.info("\n[STAGE 2] Semantic Extraction with LLM")
    logger.info("-" * 40)
    
    semantic_extractor = SemanticExtractor(llm_config)
    
    all_semantic_nodes: List[SemanticNode] = []
    all_semantic_relations: List[SemanticRelation] = []
    all_errors: List[Dict[str, Any]] = []
    
    # Process each article
    for article in structure_result.articles:
        if not article.full_text.strip():
            logger.warning(f"Skipping empty article: {article.id}")
            continue
        
        try:
            semantic_result = semantic_extractor.extract_from_article(
                article_id=article.id,
                article_title=article.title,
                article_text=article.full_text
            )
            
            all_semantic_nodes.extend(semantic_result.nodes)
            all_semantic_relations.extend(semantic_result.relations)
            
            if semantic_result.errors:
                all_errors.extend([
                    {"article_id": article.id, "error": e}
                    for e in semantic_result.errors
                ])
                
        except Exception as e:
            logger.error(f"Failed semantic extraction for {article.id}: {e}")
            all_errors.append({"article_id": article.id, "error": str(e)})
            if not continue_on_error:
                raise
    
    logger.info(
        f"Stage 2 complete: {len(all_semantic_nodes)} entities, "
        f"{len(all_semantic_relations)} relations"
    )
    
    # =========================================================================
    # Combine Results
    # =========================================================================
    hybrid_result = HybridExtractionResult(
        structure=structure_result,
        semantic_nodes=all_semantic_nodes,
        semantic_relations=all_semantic_relations,
        total_pages=structure_result.page_count,
        total_articles_processed=len(structure_result.articles),
        errors=structure_result.errors + all_errors
    )
    
    # =========================================================================
    # Convert to Graph Models
    # =========================================================================
    logger.info("\n[CONVERSION] Mapping to graph_models.py")
    logger.info("-" * 40)
    
    graph_nodes, graph_relationships = convert_to_graph_models(hybrid_result)
    
    logger.info(f"Converted: {len(graph_nodes)} GraphNodes, {len(graph_relationships)} GraphRelationships")
    
    # Save result if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(hybrid_result.model_dump(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Result saved to: {output_path}")
    
    # =========================================================================
    # Summary
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("EXTRACTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Pages processed: {hybrid_result.total_pages}")
    logger.info(f"Articles extracted: {hybrid_result.total_articles_processed}")
    logger.info(f"Semantic entities: {len(all_semantic_nodes)}")
    logger.info(f"Semantic relations: {len(all_semantic_relations)}")
    logger.info(f"GraphNodes: {len(graph_nodes)}")
    logger.info(f"GraphRelationships: {len(graph_relationships)}")
    logger.info(f"Errors: {len(hybrid_result.errors)}")
    
    return hybrid_result, graph_nodes, graph_relationships


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """
    Command-line interface for the Hybrid Two-Stage Extractor.
    
    Usage:
        # From PDF
        python hybrid_extractor.py --pdf document.pdf --output result.json
        
        # From images
        python hybrid_extractor.py --input-dir ./images --output result.json
        
    Environment variables:
        OPENROUTER_API_KEY: API key for OpenRouter
        VLM_MODEL: Model for Stage 1 (e.g., 'google/gemini-flash-1.5')
        LLM_MODEL: Model for Stage 2 (e.g., 'openai/gpt-4o-mini')
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Two-Stage Knowledge Graph Extraction for Legal Documents"
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--pdf", type=str, help="Path to PDF file")
    input_group.add_argument("--input-dir", type=str, help="Directory with page images")
    
    # Output options
    parser.add_argument(
        "--output",
        type=str,
        default="hybrid_extraction_result.json",
        help="Output JSON file (default: hybrid_extraction_result.json)"
    )
    
    # VLM options
    parser.add_argument(
        "--vlm-provider",
        type=str,
        choices=["openrouter", "openai", "gemini"],
        default="openrouter",
        help="VLM provider for Stage 1 (default: openrouter)"
    )
    
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configs
        vlm_provider = VLMProvider(args.vlm_provider)
        vlm_config = VLMConfig.from_env(provider=vlm_provider)
        llm_config = LLMConfig.from_env()
        
        print(f"VLM: {vlm_config.provider.value}/{vlm_config.model}")
        print(f"LLM: {llm_config.model}")
        print()
        
        # Run pipeline
        if args.pdf:
            result, nodes, rels = run_pipeline(
                pdf_path=Path(args.pdf),
                vlm_config=vlm_config,
                llm_config=llm_config,
                output_path=Path(args.output)
            )
        else:
            input_dir = Path(args.input_dir)
            image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
            image_paths = sorted([
                p for p in input_dir.iterdir()
                if p.suffix.lower() in image_extensions
            ])
            
            if not image_paths:
                print(f"Error: No images found in {input_dir}")
                return 1
            
            result, nodes, rels = run_pipeline(
                image_paths=image_paths,
                vlm_config=vlm_config,
                llm_config=llm_config,
                output_path=Path(args.output)
            )
        
        # Print summary
        print(f"\nOutput saved to: {args.output}")
        print(f"GraphNodes: {len(nodes)}")
        print(f"GraphRelationships: {len(rels)}")
        
        return 0
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease create a .env file with:")
        print("  OPENROUTER_API_KEY=your-api-key")
        print("  VLM_MODEL=google/gemini-flash-1.5")
        print("  LLM_MODEL=openai/gpt-4o-mini")
        return 1
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
