"""
Hybrid LlamaParse + VLM Extraction Pipeline.

This module combines the strengths of both approaches:
- LlamaParse: Superior OCR quality, table extraction, multi-page handling
- VLM: Accurate structure understanding (chapter/article boundaries)

Strategy:
1. Use LlamaParse to extract high-quality text content
2. Use VLM on a few key pages to verify/correct structure boundaries
3. Merge LlamaParse content into VLM-detected structure

Benefits:
- Better text quality than pure VLM (LlamaParse has better OCR)
- Better structure detection than pure LlamaParse (VLM understands visual layout)
- Reduced VLM API costs (only call VLM for structure verification, not all content)
- Handles tables correctly (LlamaParse strength)
- Preserves accurate chapter/article boundaries (VLM strength)

Usage:
    from app.core.extraction.hybrid_llamaparse_vlm import HybridExtractor
    
    extractor = HybridExtractor.from_env()
    result = await extractor.extract_from_pdf(pdf_path, category="Quy chế Đào tạo")
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class HybridConfig:
    """Configuration for hybrid LlamaParse + VLM extraction."""
    
    # LlamaParse settings
    llama_cloud_api_key: str = "llx-hA9tHV3v481rmzAjnyTk14iOxjpG7lCjSO4R4s9dxPhCF10k"
    llama_parse_result_type: str = "markdown"
    llama_parse_language: str = "vi"
    
    # VLM settings (for structure verification)
    vlm_provider: str = "openrouter"
    vlm_model: str = "openai/gpt-4.1"
    vlm_api_key: str = ""
    vlm_base_url: str = "https://openrouter.ai/api/v1"
    
    # Hybrid strategy settings
    vlm_sample_pages: List[int] = field(default_factory=lambda: [1, 2, 3])  # Which pages to send to VLM
    vlm_verify_structure: bool = True  # Use VLM to verify structure
    prefer_llamaparse_content: bool = True  # Use LlamaParse content over VLM content
    
    @classmethod
    def from_env(cls) -> "HybridConfig":
        """Load configuration from environment variables."""
        from dotenv import load_dotenv
        load_dotenv()
        
        return cls(
            llama_cloud_api_key=os.getenv("LLAMA_CLOUD_API_KEY", ""),
            vlm_model=os.getenv("VLM_MODEL", "openai/gpt-4.1"),
            vlm_api_key=os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", ""),
            vlm_base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        )


@dataclass
class StructureElement:
    """A structural element (chapter, article, clause, table)."""
    id: str
    type: str  # Chapter, Article, Clause, Table
    title: str
    full_text: str
    page_range: List[int]
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Result from hybrid extraction."""
    document: Optional[Dict[str, Any]] = None
    chapters: List[StructureElement] = field(default_factory=list)
    articles: List[StructureElement] = field(default_factory=list)
    clauses: List[StructureElement] = field(default_factory=list)
    tables: List[StructureElement] = field(default_factory=list)
    relations: List[Dict[str, str]] = field(default_factory=list)
    page_count: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format compatible with existing pipeline."""
        return {
            "document": self.document,
            "chapters": [
                {
                    "id": c.id,
                    "type": c.type,
                    "title": c.title,
                    "full_text": c.full_text,
                    "page_range": c.page_range,
                    "parent_id": c.parent_id,
                    "metadata": c.metadata
                }
                for c in self.chapters
            ],
            "articles": [
                {
                    "id": a.id,
                    "type": a.type,
                    "title": a.title,
                    "full_text": a.full_text,
                    "page_range": a.page_range,
                    "parent_id": a.parent_id,
                    "metadata": a.metadata
                }
                for a in self.articles
            ],
            "clauses": [
                {
                    "id": cl.id,
                    "type": cl.type,
                    "title": cl.title,
                    "full_text": cl.full_text,
                    "page_range": cl.page_range,
                    "parent_id": cl.parent_id,
                    "metadata": cl.metadata
                }
                for cl in self.clauses
            ],
            "tables": [
                {
                    "id": t.id,
                    "type": t.type,
                    "title": t.title,
                    "full_text": t.full_text,
                    "page_range": t.page_range,
                    "parent_id": t.parent_id,
                    "metadata": t.metadata
                }
                for t in self.tables
            ],
            "relations": self.relations,
            "page_count": self.page_count,
            "errors": self.errors
        }


@dataclass
class DocumentStructureTemplate:
    """
    Dynamic structure template discovered by VLM.
    
    Instead of hardcoded CHAPTER_ARTICLE_RANGES, this template is
    generated by VLM scanning the document's TOC or first pages.
    
    Supports various document types:
    - hierarchical: Quy chế with Chapters containing Articles (790, 131)
    - flat: Documents without chapters, only Articles (547, some Quyết định)
    - decision_with_attachment: Quyết định with attached Quy định (1393, 1376)
    """
    document_type: str = "hierarchical"  # hierarchical, flat, decision_with_attachment
    document_title: str = ""
    
    # For hierarchical documents
    chapters: List[Dict[str, Any]] = field(default_factory=list)
    # Format: [{"number": 1, "title": "...", "start_article": 1, "end_article": 9}]
    
    # For decision_with_attachment
    has_decision_section: bool = False  # Whether doc has Quyết định + Quy định structure
    decision_articles: List[int] = field(default_factory=list)  # Articles in Decision part
    regulation_articles: List[int] = field(default_factory=list)  # Articles in Regulation part
    regulation_start_article: int = 0  # Where the attached regulation starts
    
    # Detected metadata
    has_toc: bool = False
    toc_page: int = 0
    total_articles: int = 0
    total_chapters: int = 0
    
    def get_chapter_for_article(self, article_num: int) -> Optional[int]:
        """Determine which chapter an article belongs to based on template."""
        if self.document_type == "flat":
            return None
        
        if self.document_type == "decision_with_attachment":
            if article_num in self.decision_articles:
                return None  # Decision articles don't belong to chapters
        
        for chapter in self.chapters:
            start = chapter.get("start_article", 0)
            end = chapter.get("end_article", 999)
            if start <= article_num <= end:
                return chapter.get("number")
        
        return None
    
    def is_decision_article(self, article_num: int) -> bool:
        """Check if article belongs to Decision part (not Regulation)."""
        return article_num in self.decision_articles


class HybridExtractor:
    """
    Hybrid extractor combining LlamaParse and VLM.
    
    Workflow:
    1. Parse PDF with LlamaParse to get high-quality text
    2. Extract structure patterns (Chương, Điều, Khoản) from text
    3. Optionally use VLM on sample pages to verify structure
    4. Build final extraction result
    """
    
    # Roman numeral mapping
    ROMAN_NUMERALS = [
        (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
        (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
        (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')
    ]
    
    def __init__(self, config: HybridConfig):
        self.config = config
        self._llama_parser = None
        logger.info(f"HybridExtractor initialized with VLM: {config.vlm_model}")
    
    @classmethod
    def from_env(cls) -> "HybridExtractor":
        """Create extractor with configuration from environment."""
        config = HybridConfig.from_env()
        return cls(config)
    
    def _arabic_to_roman(self, num: int) -> str:
        """Convert Arabic numeral to Roman numeral."""
        result = []
        for value, numeral in self.ROMAN_NUMERALS:
            while num >= value:
                result.append(numeral)
                num -= value
        return ''.join(result)
    
    def _roman_to_arabic(self, roman: str) -> int:
        """Convert Roman numeral to Arabic numeral."""
        roman = roman.upper()
        roman_values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        result = 0
        prev_value = 0
        for char in reversed(roman):
            value = roman_values.get(char, 0)
            if value < prev_value:
                result -= value
            else:
                result += value
            prev_value = value
        return result
    
    def _get_llama_parser(self):
        """Lazy initialization of LlamaParse."""
        if self._llama_parser is None:
            if not self.config.llama_cloud_api_key:
                raise ValueError(
                    "LLAMA_CLOUD_API_KEY is required. "
                    "Get your key from https://cloud.llamaindex.ai/"
                )
            
            try:
                from llama_parse import LlamaParse
                
                self._llama_parser = LlamaParse(
                    api_key=self.config.llama_cloud_api_key,
                    result_type=self.config.llama_parse_result_type,
                    language=self.config.llama_parse_language,
                    verbose=True,
                    parsing_instruction="""
                    Đây là QUY CHẾ ĐÀO TẠO của trường Đại học Công nghệ Thông tin (UIT).
                    
                    CẤU TRÚC VĂN BẢN:
                    - Văn bản có 6 CHƯƠNG chính:
                      + CHƯƠNG 1: QUY ĐỊNH CHUNG (Điều 1-9)
                      + CHƯƠNG 2: TỔ CHỨC ĐÀO TẠO (Điều 10-19)
                      + CHƯƠNG 3: KIỂM TRA VÀ THI HỌC PHẦN (Điều 20-27)
                      + CHƯƠNG 4: ỨNG DỤNG CÔNG NGHỆ THÔNG TIN (Điều 28-30)
                      + CHƯƠNG 5: THỰC TẬP, KHÓA LUẬN TỐT NGHIỆP (Điều 31-34)
                      + CHƯƠNG 6: ĐIỀU KHOẢN THI HÀNH
                    
                    YÊU CẦU TRÍCH XUẤT:
                    - Giữ nguyên tiêu đề CHƯƠNG theo format: "CHƯƠNG X. [TÊN CHƯƠNG]"
                    - Giữ nguyên tiêu đề Điều theo format: "Điều X. [Tên điều]"
                    - Bảng biểu: Giữ nguyên dạng Markdown
                    - Số liệu: Điểm số, tín chỉ, tỷ lệ phần trăm
                    
                    IMPORTANT: Preserve exact chapter titles as they appear in the document header.
                    Do NOT use section subtitles as chapter titles.
                    """
                )
                logger.info("LlamaParse initialized successfully")
                
            except ImportError:
                raise ImportError(
                    "llama-parse not installed. Run: pip install llama-parse>=0.5.0"
                )
        
        return self._llama_parser
    
    async def extract_from_pdf(
        self,
        pdf_path: Path,
        category: str = "Quy chế Đào tạo"
    ) -> ExtractionResult:
        """
        Extract document structure from PDF using hybrid approach.
        
        Enhanced workflow:
        1. Parse with LlamaParse
        2. Discover document structure dynamically (VLM scans TOC/first pages)
        3. Extract structure using discovered template (not hardcoded ranges)
        4. Post-process and validate
        
        Args:
            pdf_path: Path to PDF file
            category: Document category for context
            
        Returns:
            ExtractionResult with extracted structure
        """
        pdf_path = Path(pdf_path)
        logger.info(f"🔄 Starting hybrid extraction for: {pdf_path.name}")
        
        result = ExtractionResult()
        actual_page_count = 0
        
        try:
            # Step 1: Parse with LlamaParse
            logger.info("📄 Step 1: Parsing with LlamaParse...")
            llama_content, actual_page_count = await self._parse_with_llamaparse(pdf_path)
            
            # Step 1.5: Discover document structure dynamically
            logger.info("🔍 Step 1.5: Discovering document structure...")
            structure_template = await self._discover_document_structure(
                pdf_path, llama_content, category
            )
            logger.info(f"📋 Document type: {structure_template.document_type}, "
                       f"Chapters: {structure_template.total_chapters}, "
                       f"Articles: {structure_template.total_articles}")
            
            # Step 2: Extract structure using discovered template
            logger.info("🔍 Step 2: Extracting structure from text...")
            result = self._extract_structure_from_text(llama_content, structure_template)
            
            # Set correct page count from PDF
            if actual_page_count > 0:
                result.page_count = actual_page_count
            
            # Step 2.5: Fix chapter titles (only for hierarchical docs)
            if structure_template.document_type == "hierarchical":
                logger.info("🔧 Step 2.5: Fixing chapter titles...")
                result = self._fix_chapter_titles(result, structure_template)
            
            # Step 3: Optionally verify with VLM
            logger.info(f"🔧 VLM config: verify_structure={self.config.vlm_verify_structure}, "
                       f"api_key={'SET' if self.config.vlm_api_key else 'NOT SET'}, "
                       f"model={self.config.vlm_model}")
            
            if self.config.vlm_verify_structure and self.config.vlm_api_key:
                logger.info("🔎 Step 3: Verifying structure with VLM...")
                result = await self._verify_with_vlm(pdf_path, result, llama_content)
            elif not self.config.vlm_api_key:
                logger.warning("⚠️ VLM API key not set, skipping VLM verification")
            else:
                logger.info("ℹ️ VLM verification disabled in config")
            
            logger.info(f"✅ Extraction complete: {len(result.chapters)} chapters, "
                       f"{len(result.articles)} articles, {len(result.clauses)} clauses, "
                       f"{len(result.tables)} tables")
            
            # Step 4: Post-processing (fix relations, remove duplicates, etc.)
            logger.info("🔧 Step 4: Running post-processing...")
            result = self._post_process_result(result, structure_template)
            
        except Exception as e:
            logger.error(f"❌ Hybrid extraction failed: {e}")
            result.errors.append(str(e))
        
        return result
    
    def _fix_chapter_titles(
        self, 
        result: ExtractionResult,
        template: Optional[DocumentStructureTemplate] = None
    ) -> ExtractionResult:
        """
        Fix chapter titles based on discovered structure template or standard mapping.
        
        For known documents (Quy chế 790), uses standard titles.
        For other documents, uses VLM-discovered titles from template.
        """
        # If template has chapter titles, use them
        if template and template.chapters:
            chapter_title_map = {
                str(ch["number"]): ch.get("title", f"CHƯƠNG {ch['number']}")
                for ch in template.chapters
            }
        else:
            # Fallback to standard Quy chế Đào tạo UIT titles
            chapter_title_map = {
                "1": "CHƯƠNG 1. QUY ĐỊNH CHUNG",
                "2": "CHƯƠNG 2. TỔ CHỨC ĐÀO TẠO", 
                "3": "CHƯƠNG 3. KIỂM TRA VÀ THI HỌC PHẦN",
                "4": "CHƯƠNG 4. ỨNG DỤNG CÔNG NGHỆ THÔNG TIN TRONG TỔ CHỨC - QUẢN LÝ ĐÀO TẠO",
                "5": "CHƯƠNG 5. THỰC TẬP, KHÓA LUẬN TỐT NGHIỆP VÀ CÔNG NHẬN TỐT NGHIỆP",
                "6": "CHƯƠNG 6. ĐIỀU KHOẢN THI HÀNH",
            }
        
        # Keywords that indicate wrong chapter titles (section subtitles)
        WRONG_TITLE_KEYWORDS = [
            "Tổ chức lớp",
            "Đăng ký học",
            "thông báo kế hoạch",
            "ngoại ngữ",
            "Không hoàn tất",
            "Điểm Miễn",
        ]
        
        for chapter in result.chapters:
            chapter_num = chapter.metadata.get("chapter_number", "")
            
            # Check if current title looks wrong
            is_wrong_title = any(kw.lower() in chapter.title.lower() for kw in WRONG_TITLE_KEYWORDS)
            
            # Also check if title doesn't start with proper format
            proper_format = chapter.title.upper().startswith(f"CHƯƠNG {chapter_num}.")
            
            if is_wrong_title or (chapter_num in chapter_title_map and not proper_format):
                old_title = chapter.title
                chapter.title = chapter_title_map.get(str(chapter_num), chapter.title)
                logger.info(f"📝 Fixed chapter title: '{old_title[:50]}...' -> '{chapter.title}'")
        
        return result
    
    async def _discover_document_structure(
        self,
        pdf_path: Path,
        content: str,
        category: str
    ) -> DocumentStructureTemplate:
        """
        Discover document structure dynamically using VLM and text analysis.
        
        This replaces hardcoded CHAPTER_ARTICLE_RANGES with dynamic detection.
        
        Steps:
        1. Quick regex scan to detect chapters and articles
        2. Detect document type (hierarchical, flat, decision_with_attachment)
        3. If hierarchical, use VLM to get chapter-article mappings
        4. Return template for use in extraction
        """
        template = DocumentStructureTemplate()
        
        # Step 1: Quick regex analysis
        chapters_found = list(re.finditer(
            r'CHƯƠNG\s+([IVXLCDM1-9]+)[\.\s:：]+([^\n]+)',
            content, re.IGNORECASE
        ))
        
        # More permissive article pattern - match "Điều X" at start of line
        # Allow for various formatting (bullets, markdown headers, etc.)
        articles_found = list(re.finditer(
            r'^[\s\-\*#]*Điều\s+(\d+)',
            content, re.MULTILINE
        ))
        
        # Log detected articles for debugging
        detected_article_nums = sorted([int(m.group(1)) for m in articles_found])
        logger.info(f"📋 Detected {len(articles_found)} articles: {detected_article_nums[:20]}{'...' if len(detected_article_nums) > 20 else ''}")
        
        # Check for gaps in article numbers
        if detected_article_nums:
            expected_range = set(range(1, max(detected_article_nums) + 1))
            missing_articles = expected_range - set(detected_article_nums)
            if missing_articles:
                logger.warning(f"⚠️ Missing articles in sequence: {sorted(missing_articles)}")
        
        template.total_chapters = len(chapters_found)
        template.total_articles = len(articles_found)
        
        # Step 2: Detect document type
        # Check for "Quyết định" pattern
        is_decision = bool(re.search(
            r'QUYẾT\s+ĐỊNH|Quyết\s+định.*?ban\s+hành',
            content[:2000], re.IGNORECASE
        ))
        
        # Check for "Quy định kèm theo" or "Quy chế"
        has_attachment = bool(re.search(
            r'(?:Quy\s+(?:định|chế)|QUY\s+(?:ĐỊNH|CHẾ)).*?(?:kèm\s+theo|ban\s+hành)',
            content[:3000], re.IGNORECASE
        ))
        
        if template.total_chapters == 0:
            template.document_type = "flat"
            logger.info("📋 Detected flat document (no chapters)")
        elif is_decision and has_attachment:
            template.document_type = "decision_with_attachment"
            template.has_decision_section = True
            
            # Detect which articles are in the Decision part vs Regulation part
            # Pattern: Decision usually has Điều 1, 2, 3 before "CHƯƠNG I"
            first_chapter_pos = chapters_found[0].start() if chapters_found else len(content)
            
            decision_articles = []
            for match in articles_found:
                if match.start() < first_chapter_pos:
                    article_num = int(match.group(1))
                    decision_articles.append(article_num)
            
            template.decision_articles = decision_articles
            logger.info(f"📋 Detected decision with attachment. "
                       f"Decision articles: {decision_articles}")
        else:
            template.document_type = "hierarchical"
            logger.info("� Detected hierarchical document with chapters")
        
        # Step 3: Build chapter-article mappings
        if template.document_type == "hierarchical" and chapters_found:
            template.chapters = self._build_chapter_article_mapping(
                content, chapters_found, articles_found
            )
        
        # Step 4: Detect TOC
        toc_match = re.search(r'MỤC\s+LỤC|NỘI\s+DUNG', content[:5000], re.IGNORECASE)
        if toc_match:
            template.has_toc = True
            # Estimate TOC page
            template.toc_page = content[:toc_match.start()].count('---') + 1
        
        # Store document title
        title_match = re.search(
            r'(?:QUY\s+CHẾ|QUY\s+ĐỊNH|QUYẾT\s+ĐỊNH)[^\n]*',
            content[:2000], re.IGNORECASE
        )
        if title_match:
            template.document_title = title_match.group(0).strip()
        
        return template
    
    def _build_chapter_article_mapping(
        self,
        content: str,
        chapters_found: List,
        articles_found: List
    ) -> List[Dict[str, Any]]:
        """
        Build chapter-article mapping by analyzing positions in text.
        
        This dynamically determines which articles belong to which chapter
        instead of using hardcoded ranges.
        """
        chapter_mappings = []
        
        # Get positions of chapters
        chapter_positions = []
        for match in chapters_found:
            chapter_num_raw = match.group(1).upper()
            # Convert Roman to Arabic if needed
            if chapter_num_raw.isdigit():
                chapter_num = int(chapter_num_raw)
            else:
                chapter_num = self._roman_to_arabic(chapter_num_raw)
            
            chapter_positions.append({
                "number": chapter_num,
                "title": f"CHƯƠNG {chapter_num}. {match.group(2).strip()}",
                "position": match.start(),
                "articles": []
            })
        
        # Sort chapters by position
        chapter_positions.sort(key=lambda x: x["position"])
        
        logger.info(f"📍 Chapter positions: {[(cp['number'], cp['position']) for cp in chapter_positions]}")
        
        # Articles that appear BEFORE first chapter
        preamble_articles = []
        first_chapter_pos = chapter_positions[0]["position"] if chapter_positions else len(content)
        
        # Assign articles to chapters based on position
        for match in articles_found:
            article_num = int(match.group(1))
            article_pos = match.start()
            
            # Handle articles before first chapter
            if article_pos < first_chapter_pos:
                preamble_articles.append(article_num)
                logger.debug(f"Article {article_num} at position {article_pos} is before first chapter ({first_chapter_pos})")
                continue
            
            # Find which chapter this article belongs to
            assigned_chapter = None
            for i, chapter in enumerate(chapter_positions):
                next_chapter_pos = (
                    chapter_positions[i + 1]["position"]
                    if i + 1 < len(chapter_positions)
                    else len(content)
                )
                
                if chapter["position"] <= article_pos < next_chapter_pos:
                    assigned_chapter = chapter
                    break
            
            if assigned_chapter:
                assigned_chapter["articles"].append(article_num)
        
        # IMPORTANT: Assign preamble articles to first chapter
        # In Vietnamese regulations, articles before "CHƯƠNG I" usually belong to Chapter 1
        if preamble_articles and chapter_positions:
            logger.info(f"📝 Found {len(preamble_articles)} preamble articles before CHƯƠNG 1: {preamble_articles}")
            chapter_positions[0]["articles"].extend(preamble_articles)
        
        # Build final mapping with start/end article ranges
        for chapter in chapter_positions:
            articles = sorted(chapter["articles"])
            if articles:
                chapter_mappings.append({
                    "number": chapter["number"],
                    "title": chapter["title"],
                    "start_article": min(articles),
                    "end_article": max(articles),
                    "article_count": len(articles)
                })
                logger.info(f"📑 Chapter {chapter['number']}: Articles {min(articles)}-{max(articles)} ({len(articles)} total)")
        
        return chapter_mappings

    def _post_process_result(
        self, 
        result: ExtractionResult,
        template: Optional[DocumentStructureTemplate] = None
    ) -> ExtractionResult:
        """
        Post-process extraction result to fix common issues.
        
        Uses template for dynamic chapter-article mapping if available,
        otherwise skips chapter-based fixes.
        
        Fixes:
        - Self-referencing relations (dieu_1 CONTAINS dieu_1)
        - Wrong chapter-article mappings (using template)
        - Duplicate relations
        - Chapter full_text containing all article content
        - Content bleeding (article containing other articles/chapters)
        - Header/footer removal
        """
        # Build dynamic chapter-article mapping from template
        chapter_article_ranges = {}
        
        if template and template.chapters:
            for ch in template.chapters:
                ch_num = ch.get("chapter") or ch.get("number")
                start = ch.get("start_article")
                end = ch.get("end_article")
                if ch_num and start and end:
                    chapter_article_ranges[int(ch_num)] = (int(start), int(end))
            
            logger.info(f"📋 Using dynamic chapter mapping: {chapter_article_ranges}")
        else:
            logger.warning("⚠️ No template available, skipping chapter-based fixes")
        
        def get_chapter_for_article(article_num: int) -> Optional[int]:
            """Determine correct chapter for an article number using template."""
            if not chapter_article_ranges:
                return None  # Can't determine without template
            
            for chapter_num, (start, end) in chapter_article_ranges.items():
                if start <= article_num <= end:
                    return chapter_num
            return None  # Article not in any chapter range
        
        # Step 1: Fix article parent_id based on article number (only if template exists)
        if chapter_article_ranges:
            for article in result.articles:
                article_num = article.metadata.get("article_number")
                if article_num:
                    # Skip decision articles (they don't have chapter parent)
                    if template and template.has_decision_section:
                        if article_num in template.decision_articles:
                            continue
                    
                    correct_chapter = get_chapter_for_article(int(article_num))
                    if correct_chapter:
                        correct_parent_id = f"chuong_{correct_chapter}"
                        if article.parent_id != correct_parent_id:
                            logger.debug(f"Fixed {article.id} parent: {article.parent_id} -> {correct_parent_id}")
                            article.parent_id = correct_parent_id
        
        # Step 2: Clean article full_text (remove content bleeding)
        for article in result.articles:
            article.full_text = self._clean_article_content(article.full_text, article.id)
        
        # Step 3: Remove self-referencing relations and rebuild correctly
        cleaned_relations = []
        seen_relations = set()
        self_refs_removed = 0
        
        for rel in result.relations:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "")
            
            # Skip self-references
            if source == target:
                self_refs_removed += 1
                continue
            
            # Skip duplicates
            rel_key = (source, target, rel_type)
            if rel_key in seen_relations:
                continue
            seen_relations.add(rel_key)
            
            # Fix chapter-article relations (only if template exists)
            if chapter_article_ranges and rel_type == "CONTAINS":
                if source.startswith("chuong_") and target.startswith("dieu_"):
                    article_match = re.search(r'dieu_(\d+)', target)
                    if article_match:
                        article_num = int(article_match.group(1))
                        correct_chapter = get_chapter_for_article(article_num)
                        if correct_chapter:
                            rel["source"] = f"chuong_{correct_chapter}"
            
            cleaned_relations.append(rel)
        
        result.relations = cleaned_relations
        if self_refs_removed > 0:
            logger.info(f"🗑️ Removed {self_refs_removed} self-referencing relations")
        
        # Step 4: Clean chapter full_text (remove duplicate article content)
        for chapter in result.chapters:
            full_text = chapter.full_text
            if not full_text:
                continue
            
            # Remove header/footer patterns
            full_text = self._remove_headers_footers(full_text)
            
            # Special handling for last chapter - remove glossary content
            # (Dynamically determine last chapter instead of hardcoding "chuong_6")
            chapter_nums = [int(ch.metadata.get("chapter_number", 0)) for ch in result.chapters]
            max_chapter = max(chapter_nums) if chapter_nums else 0
            if chapter.metadata.get("chapter_number") == str(max_chapter):
                full_text = self._clean_chapter_6(full_text)
            
            # Find where first article starts
            first_article_match = re.search(r'Điều\s+\d+', full_text)
            if first_article_match:
                # Keep only content before first article
                intro_text = full_text[:first_article_match.start()].strip()
                
                # If intro is too short, keep chapter title
                if len(intro_text) < 20:
                    intro_text = chapter.title
                
                # Limit to reasonable length
                if len(intro_text) > 500:
                    intro_text = intro_text[:500] + "..."
                
                chapter.full_text = intro_text
                logger.debug(f"Cleaned {chapter.id} full_text: {len(full_text)} -> {len(intro_text)} chars")
        
        return result
    
    def _clean_article_content(self, content: str, article_id: str) -> str:
        """
        Clean article content by removing:
        - Content from other articles (content bleeding)
        - Chapter titles that got mixed in
        - Headers/footers
        - Trailing incomplete content
        """
        if not content:
            return content
        
        # Remove headers/footers first
        content = self._remove_headers_footers(content)
        
        # Remove any chapter titles/headers that got mixed in
        # Pattern matches: "CHƯƠNG X. Title" or "CHƯƠNG X:" etc.
        content = re.sub(
            r'\n*[\s#]*CHƯƠNG\s+[IVXLCDM0-9]+[\.\s:：]+[^\n]*\n*',
            '\n', 
            content, 
            flags=re.IGNORECASE
        )
        
        # Find and remove content from other articles
        # Look for "Điều X" patterns that indicate another article started
        article_match = re.search(r'dieu_(\d+)', article_id)
        current_article_num = int(article_match.group(1)) if article_match else 0
        
        # Find where another article starts (not the current one)
        # More robust pattern - article at start of line
        other_article_pattern = r'^[\s\-\*#]*Điều\s+(\d+)[\.\s:：]'
        for match in re.finditer(other_article_pattern, content, re.MULTILINE):
            found_article_num = int(match.group(1))
            if found_article_num != current_article_num:
                # Cut content before this other article
                content = content[:match.start()].strip()
                logger.debug(f"Removed bleeding content from {article_id}: found Điều {found_article_num}")
                break
        
        # Also check for inline article references that look like headers
        # e.g., "Điều 10. Tên điều" appearing inline
        inline_article = re.search(r'\n\s*Điều\s+(\d+)[\.\s:：]', content)
        if inline_article:
            found_article_num = int(inline_article.group(1))
            if found_article_num != current_article_num:
                content = content[:inline_article.start()].strip()
                logger.debug(f"Removed inline bleeding from {article_id}: found Điều {found_article_num}")
        
        # Clean up multiple newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    def _remove_headers_footers(self, content: str) -> str:
        """Remove common headers and footers from content."""
        # Remove page numbers like "Trang X/Y" or "Trang X"
        content = re.sub(r'Trang\s+\d+\s*/\s*\d+', '', content)
        content = re.sub(r'Trang\s+\d+', '', content)
        
        # Remove repeated document titles/headers
        content = re.sub(r'QUY CHẾ ĐÀO TẠO.*?(?=\n)', '', content, flags=re.IGNORECASE)
        
        # Remove "---" page separators that LlamaParse adds
        content = re.sub(r'\n-{3,}\n', '\n', content)
        
        # Remove empty lines created by removals
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    def _clean_chapter_6(self, content: str) -> str:
        """
        Special cleaning for Chapter 6.
        Remove glossary/abbreviation content that doesn't belong.
        """
        # Remove "Danh mục từ viết tắt" section
        content = re.sub(
            r'Danh\s+mục\s+từ\s+viết\s+tắt.*?(?=Điều|\Z)',
            '',
            content,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # Remove common glossary patterns
        glossary_patterns = [
            r'[A-Z]{2,}:\s*[^\n]+\n',  # Abbreviations like "ĐHQG: Đại học Quốc gia"
            r'(?:Bằng|Chứng chỉ|Văn bằng)\s+\w+:.*?\n',  # Certificate definitions
        ]
        
        for pattern in glossary_patterns:
            content = re.sub(pattern, '', content)
        
        return content.strip()

    async def _parse_with_llamaparse(self, pdf_path: Path) -> Tuple[str, int]:
        """Parse PDF with LlamaParse and return content with page-level merging.
        
        Returns:
            Tuple of (merged_content, actual_page_count)
        """
        parser = self._get_llama_parser()
        
        # Run in thread pool to avoid blocking
        documents = await asyncio.to_thread(
            parser.load_data, str(pdf_path)
        )
        
        if not documents:
            raise ValueError(f"No content extracted from {pdf_path}")
        
        # Get actual page count from PDF using PyMuPDF
        actual_page_count = self._get_pdf_page_count(pdf_path)
        
        # Apply page-level text merging to handle cross-page content
        merged_content = self._merge_pages_with_pending_text(documents)
        
        logger.info(f"📄 LlamaParse extracted {len(documents)} document(s), "
                   f"PDF has {actual_page_count} pages, "
                   f"{len(merged_content)} characters after merging")
        
        return merged_content, actual_page_count
    
    def _get_pdf_page_count(self, pdf_path: Path) -> int:
        """Get actual page count from PDF file."""
        try:
            import fitz  # PyMuPDF
            with fitz.open(str(pdf_path)) as doc:
                return len(doc)
        except ImportError:
            logger.warning("PyMuPDF not installed, using estimate for page count")
            return 0
        except Exception as e:
            logger.warning(f"Could not read PDF page count: {e}")
            return 0
    
    def _merge_pages_with_pending_text(self, documents: List) -> str:
        """
        Merge page content with pending_text logic.
        
        If a page ends with an incomplete sentence (no period, ends with
        connector words like 'tại', 'của', 'và'), carry it over to the next page.
        
        This prevents truncation at page boundaries.
        """
        # Patterns that indicate incomplete sentence at end of page
        INCOMPLETE_END_PATTERNS = [
            r',\s*$',                    # Ends with comma
            r';\s*$',                    # Ends with semicolon  
            r':\s*$',                    # Ends with colon
            r'\s+tại\s*$',               # Ends with "tại"
            r'\s+của\s*$',               # Ends with "của"
            r'\s+và\s*$',                # Ends with "và"
            r'\s+hoặc\s*$',              # Ends with "hoặc"
            r'\s+là\s*$',                # Ends with "là"
            r'\s+được\s*$',              # Ends with "được"
            r'\s+theo\s*$',              # Ends with "theo"
            r'\s+cho\s*$',               # Ends with "cho"
            r'\s+với\s*$',               # Ends with "với"
            r'[Kk]hoản\s+\d+\s*,?\s*$',  # Ends with "Khoản X,"
            r'[Đđ]iều\s+\d+\s*,?\s*$',   # Ends with "Điều X,"
        ]
        
        merged_pages = []
        pending_text = ""
        
        for i, doc in enumerate(documents):
            page_text = doc.text.strip()
            
            # Remove headers/footers from page
            page_text = self._remove_headers_footers(page_text)
            
            # Prepend pending text from previous page
            if pending_text:
                # Find where content starts (skip any repeated headers)
                # and merge pending text
                page_text = pending_text + " " + page_text
                pending_text = ""
                logger.debug(f"Page {i+1}: Merged pending text from previous page")
            
            # Check if page ends with incomplete sentence
            is_incomplete = False
            for pattern in INCOMPLETE_END_PATTERNS:
                if re.search(pattern, page_text):
                    is_incomplete = True
                    break
            
            # Also check if last line doesn't end with sentence-ending punctuation
            if not is_incomplete:
                last_100_chars = page_text[-100:] if len(page_text) > 100 else page_text
                if not re.search(r'[.!?]\s*$', last_100_chars):
                    # Check if it ends mid-word or mid-phrase
                    if not re.search(r'[.!?]\s*$', page_text):
                        is_incomplete = True
            
            if is_incomplete and i < len(documents) - 1:
                # Find the last complete sentence
                # Look for last period that's not part of "Điều X." or "Khoản X."
                last_complete = -1
                for m in re.finditer(r'(?<=[^0-9Đđ])[.!?]\s', page_text):
                    last_complete = m.end()
                
                if last_complete > 0 and last_complete < len(page_text) - 50:
                    # Split: keep complete part, carry over incomplete part
                    pending_text = page_text[last_complete:].strip()
                    page_text = page_text[:last_complete].strip()
                    logger.debug(f"Page {i+1}: Carrying over {len(pending_text)} chars to next page")
                else:
                    # Can't find good split point, carry over last line
                    last_newline = page_text.rfind('\n')
                    if last_newline > len(page_text) * 0.8:
                        pending_text = page_text[last_newline:].strip()
                        page_text = page_text[:last_newline].strip()
                        logger.debug(f"Page {i+1}: Carrying over last line to next page")
            
            merged_pages.append(page_text)
        
        # Handle any remaining pending text
        if pending_text and merged_pages:
            merged_pages[-1] += " " + pending_text
        
        return "\n\n---\n\n".join(merged_pages)
    
    def _extract_with_template(
        self, 
        content: str, 
        template: DocumentStructureTemplate
    ) -> ExtractionResult:
        """
        Extract document structure using a discovered template.
        
        This method uses the pre-analyzed chapter-article mapping from the template
        instead of hardcoded values, making it work for any UIT document.
        """
        result = ExtractionResult()
        result.page_count = content.count("---") + 1
        
        logger.info(f"🔧 Using template-based extraction ({template.document_type})")
        
        # Build chapter info from template
        chapter_info = {}  # chapter_num -> {"title": ..., "start": ..., "end": ...}
        for ch in template.chapters:
            ch_num = ch.get("chapter")
            chapter_info[ch_num] = {
                "title": ch.get("title", ""),
                "start_article": ch.get("start_article"),
                "end_article": ch.get("end_article"),
            }
        
        # Extract chapters from content
        chapter_pattern = r'^[\s#]*CHƯƠNG\s+([1-9]|[IVXLCDM]+)[\.\s:：]+([^\n]+)'
        chapter_positions = []
        
        for match in re.finditer(chapter_pattern, content, re.MULTILINE | re.IGNORECASE):
            chapter_num_raw = match.group(1).upper()
            chapter_title_raw = match.group(2).strip()
            
            # Convert to Arabic
            if chapter_num_raw.isdigit():
                chapter_num = int(chapter_num_raw)
            else:
                chapter_num = self._roman_to_arabic(chapter_num_raw)
            
            # Use template title if available (more reliable)
            chapter_title = chapter_title_raw
            if chapter_num in chapter_info:
                template_title = chapter_info[chapter_num].get("title", "")
                if template_title:
                    chapter_title = template_title
            
            chapter_id = f"chuong_{chapter_num}"
            
            # Find chapter content
            start_pos = match.end()
            next_chapter = re.search(
                r'^[\s#]*CHƯƠNG\s+([1-9]|[IVXLCDM]+)', 
                content[start_pos:], 
                re.MULTILINE | re.IGNORECASE
            )
            end_pos = start_pos + next_chapter.start() if next_chapter else len(content)
            chapter_content = content[start_pos:end_pos].strip()
            
            chapter = StructureElement(
                id=chapter_id,
                type="Chapter",
                title=f"CHƯƠNG {chapter_num}. {chapter_title}".strip(),
                full_text=chapter_content[:2000],
                page_range=[1],
                metadata={
                    "chapter_number": str(chapter_num),
                    "from_template": True
                }
            )
            result.chapters.append(chapter)
            chapter_positions.append((match.start(), chapter_id, chapter_num))
            logger.info(f"📑 Template: Chapter {chapter_num} - {chapter_title[:40]}")
        
        chapter_positions.sort(key=lambda x: x[0])
        
        # Extract articles and assign parent using template
        # More permissive pattern to catch various formatting
        article_pattern = r'^[\s\-\*#]*Điều\s+(\d+)[\.\s:：]*([^\n]*)'
        
        for match in re.finditer(article_pattern, content, re.MULTILINE):
            article_num = int(match.group(1))
            article_title = match.group(2).strip() if match.group(2) else ""
            article_id = f"dieu_{article_num}"
            
            # Find article content
            start_pos = match.end()
            next_article = re.search(r'^[\s\-\*#]*Điều\s+\d+', content[start_pos:], re.MULTILINE)
            next_chapter = re.search(
                r'^[\s#]*CHƯƠNG\s+([1-9]|[IVXLCDM]+)', 
                content[start_pos:], 
                re.MULTILINE | re.IGNORECASE
            )
            
            end_pos = len(content)
            if next_article:
                end_pos = min(end_pos, start_pos + next_article.start())
            if next_chapter:
                end_pos = min(end_pos, start_pos + next_chapter.start())
            
            article_content = content[start_pos:end_pos].strip()
            
            # Fix truncation
            article_content, is_truncated = self._fix_truncated_content(
                article_content, content, start_pos, end_pos
            )
            
            # IMPORTANT: Use template to determine parent chapter
            parent_chapter_id = None
            
            # First check if it's a decision article (no chapter)
            if template.has_decision_section and article_num in template.decision_articles:
                parent_chapter_id = None  # Decision articles don't have chapter parent
                logger.debug(f"Article {article_num} is a decision article (no chapter)")
            else:
                # Find chapter using template mapping
                parent_chapter_id = self._get_chapter_from_template(
                    article_num, chapter_info, chapter_positions, match.start()
                )
            
            article = StructureElement(
                id=article_id,
                type="Article",
                title=f"Điều {article_num}. {article_title}".strip(),
                full_text=article_content,
                page_range=[1],
                parent_id=parent_chapter_id,
                metadata={
                    "article_number": article_num,
                    "is_truncated": is_truncated,
                    "is_decision_article": template.has_decision_section and article_num in template.decision_articles
                }
            )
            result.articles.append(article)
            
            # Add CONTAINS relation
            if parent_chapter_id:
                result.relations.append({
                    "source": parent_chapter_id,
                    "target": article_id,
                    "type": "CONTAINS"
                })
            
            # Extract clauses
            clauses = self._extract_clauses(article_content, article_id)
            result.clauses.extend(clauses)
            for clause in clauses:
                result.relations.append({
                    "source": article_id,
                    "target": clause.id,
                    "type": "CONTAINS"
                })
        
        # Extract tables and glossary
        tables = self._extract_tables(content)
        result.tables.extend(tables)
        
        glossary = self._extract_glossary(content)
        if glossary:
            result.tables.append(glossary)
        
        logger.info(f"✅ Template extraction: {len(result.chapters)} chapters, "
                   f"{len(result.articles)} articles, {len(result.clauses)} clauses")
        
        return result
    
    def _get_chapter_from_template(
        self,
        article_num: int,
        chapter_info: Dict[int, Dict],
        chapter_positions: List[Tuple[int, str, int]],
        article_pos: int
    ) -> Optional[str]:
        """
        Determine parent chapter for an article using template info.
        
        Priority:
        1. Use template's start_article/end_article range
        2. Fall back to position-based detection
        """
        # Method 1: Use template ranges
        for ch_num, info in chapter_info.items():
            start = info.get("start_article")
            end = info.get("end_article")
            if start is not None and end is not None:
                if start <= article_num <= end:
                    return f"chuong_{ch_num}"
        
        # Method 2: Fall back to position-based
        for ch_pos, ch_id, ch_num in reversed(chapter_positions):
            if ch_pos < article_pos:
                return ch_id
        
        return None

    def _extract_structure_from_text(
        self, 
        content: str, 
        structure_template: Optional[DocumentStructureTemplate] = None
    ) -> ExtractionResult:
        """
        Extract document structure from LlamaParse text content.
        
        If structure_template is provided, use it for dynamic chapter-article mapping.
        Otherwise, fall back to regex-based detection.
        
        Uses regex patterns to identify:
        - Chapters (CHƯƠNG X)
        - Articles (Điều X)
        - Clauses (Khoản X / 1., 2., a), b))
        - Tables (Markdown format)
        """
        result = ExtractionResult()
        result.page_count = content.count("---") + 1  # Estimate pages
        
        # If we have a template with chapters, use it
        if structure_template and structure_template.chapters:
            return self._extract_with_template(content, structure_template)
        
        # Otherwise, fall back to regex-based extraction
        # Extract chapters - IMPROVED pattern
        # Only match CHƯƠNG followed by Roman numerals (I, II, III...) or single digits 1-9
        # Avoid matching "CHƯƠNG 22" which is likely a reference to Điều 22
        chapter_pattern = r'^[\s#]*CHƯƠNG\s+([1-9]|[IVXLCDM]+)[\.\s:：]+([^\n]+)'
        
        for match in re.finditer(chapter_pattern, content, re.MULTILINE | re.IGNORECASE):
            chapter_num_raw = match.group(1).upper()
            chapter_title = match.group(2).strip()
            
            # Convert Roman numerals to Arabic for consistent IDs
            if chapter_num_raw.isdigit():
                chapter_num = chapter_num_raw
            else:
                # It's a Roman numeral, convert to Arabic
                chapter_num = str(self._roman_to_arabic(chapter_num_raw))
            
            # Skip if chapter number is too high (likely a Điều reference)
            if int(chapter_num) > 10:
                logger.debug(f"Skipping likely Điều reference: CHƯƠNG {chapter_num_raw}")
                continue
            
            chapter_id = f"chuong_{chapter_num}"
            full_match = f"CHƯƠNG {chapter_num}. {chapter_title}"
            
            # Find chapter content (until next chapter or end)
            start_pos = match.end()
            next_chapter = re.search(r'^[\s#]*CHƯƠNG\s+([1-9]|[IVXLCDM]+)', content[start_pos:], re.MULTILINE | re.IGNORECASE)
            end_pos = start_pos + next_chapter.start() if next_chapter else len(content)
            chapter_content = content[start_pos:end_pos].strip()
            
            chapter = StructureElement(
                id=chapter_id,
                type="Chapter",
                title=full_match.strip(),
                full_text=chapter_content[:2000],  # Limit content length
                page_range=[1],  # Will be refined by VLM
                metadata={"chapter_number": chapter_num}
            )
            result.chapters.append(chapter)
            logger.info(f"📑 Found chapter: {chapter_id} - {chapter_title[:50]}")
        
        # Build chapter position map for parent detection
        # Need to search for both Arabic (1,2,3) and Roman numerals (I,II,III)
        chapter_positions = []
        for chapter in result.chapters:
            chapter_num = chapter.metadata.get("chapter_number", "")
            
            # Try to find chapter with Arabic numeral first
            chapter_match = re.search(
                rf'CHƯƠNG\s+{re.escape(chapter_num)}[\.\s:：]',
                content, re.IGNORECASE
            )
            
            # If not found, try Roman numeral equivalent
            if not chapter_match and chapter_num.isdigit():
                roman_num = self._arabic_to_roman(int(chapter_num))
                chapter_match = re.search(
                    rf'CHƯƠNG\s+{roman_num}[\.\s:：]',
                    content, re.IGNORECASE
                )
            
            if chapter_match:
                chapter_positions.append((chapter_match.start(), chapter.id))
                logger.debug(f"Chapter {chapter.id} found at position {chapter_match.start()}")
        
        chapter_positions.sort(key=lambda x: x[0])
        logger.info(f"📍 Found {len(chapter_positions)} chapter positions for parent mapping")
        
        # IMPROVED: Article pattern - more permissive to catch various formatting
        # Allow markdown bullets/headers, whitespace variations
        article_pattern = r'^[\s\-\*#]*Điều\s+(\d+)[\.\s:：]*([^\n]*)'
        
        for match in re.finditer(article_pattern, content, re.MULTILINE):
            article_num = match.group(1)
            article_title = match.group(2).strip() if match.group(2) else ""
            full_match = f"Điều {article_num}. {article_title}".strip()
            
            article_id = f"dieu_{article_num}"
            
            # Find article content (until next article or chapter)
            start_pos = match.end()
            # Use same permissive pattern to find next article
            next_article = re.search(r'^[\s\-\*#]*Điều\s+\d+', content[start_pos:], re.MULTILINE)
            next_chapter = re.search(r'^[\s#]*CHƯƠNG\s+([1-9]|[IVXLCDM]+)', content[start_pos:], re.MULTILINE | re.IGNORECASE)
            
            end_pos = len(content)
            if next_article:
                end_pos = min(end_pos, start_pos + next_article.start())
            if next_chapter:
                end_pos = min(end_pos, start_pos + next_chapter.start())
            
            article_content = content[start_pos:end_pos].strip()
            
            # Check and fix truncation
            article_content, is_truncated = self._fix_truncated_content(
                article_content, content, start_pos, end_pos
            )
            
            # Determine parent chapter based on position
            current_chapter_id = None
            article_pos = match.start()
            for ch_pos, ch_id in reversed(chapter_positions):
                if ch_pos < article_pos:
                    current_chapter_id = ch_id
                    break
            
            article = StructureElement(
                id=article_id,
                type="Article",
                title=full_match.strip(),
                full_text=article_content,
                page_range=[1],  # Will be refined
                parent_id=current_chapter_id,
                metadata={
                    "article_number": int(article_num),
                    "is_truncated": is_truncated
                }
            )
            result.articles.append(article)
            
            # Add CONTAINS relation
            if current_chapter_id:
                result.relations.append({
                    "source": current_chapter_id,
                    "target": article_id,
                    "type": "CONTAINS"
                })
            
            # Extract clauses within this article
            clauses = self._extract_clauses(article_content, article_id)
            result.clauses.extend(clauses)
            for clause in clauses:
                result.relations.append({
                    "source": article_id,
                    "target": clause.id,
                    "type": "CONTAINS"
                })
        
        # Extract tables
        tables = self._extract_tables(content)
        result.tables.extend(tables)
        
        # Extract glossary as separate category (not part of chuong_6)
        glossary = self._extract_glossary(content)
        if glossary:
            result.tables.append(glossary)  # Store glossary with tables
            logger.info(f"📚 Extracted glossary with {len(glossary.full_text)} chars")
        
        return result
    
    def _extract_glossary(self, content: str) -> Optional[StructureElement]:
        """
        Extract glossary (Danh mục từ viết tắt) as a separate node.
        
        This prevents it from being included in Chapter 6 content.
        """
        # Pattern to find glossary section
        glossary_patterns = [
            r'(?:DANH\s+MỤC|Danh\s+mục)\s+(?:TỪ\s+VIẾT\s+TẮT|từ\s+viết\s+tắt|CÁC\s+TỪ\s+VIẾT\s+TẮT)',
            r'(?:PHỤ\s+LỤC|Phụ\s+lục).*?(?:TỪ\s+VIẾT\s+TẮT|từ\s+viết\s+tắt)',
        ]
        
        glossary_start = -1
        glossary_title = "Danh mục từ viết tắt"
        
        for pattern in glossary_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                glossary_start = match.start()
                glossary_title = match.group(0).strip()
                break
        
        if glossary_start < 0:
            return None
        
        # Find end of glossary (next chapter or major section)
        remaining = content[glossary_start:]
        glossary_end = len(remaining)
        
        # Look for end markers
        end_patterns = [
            r'\n\s*CHƯƠNG\s+[IVXLCDM1-9]+',
            r'\n\s*Điều\s+\d+',
            r'\n\s*(?:MỤC|Mục)\s+[IVXLCDM1-9]+',
        ]
        
        for pattern in end_patterns:
            match = re.search(pattern, remaining, re.IGNORECASE)
            if match:
                glossary_end = min(glossary_end, match.start())
        
        glossary_content = remaining[:glossary_end].strip()
        
        # Parse glossary into structured format
        glossary_items = []
        abbreviation_pattern = r'([A-ZĐĂÂÊÔƠƯ]{2,})\s*[:\-–]\s*([^\n]+)'
        
        for match in re.finditer(abbreviation_pattern, glossary_content):
            abbrev = match.group(1).strip()
            meaning = match.group(2).strip()
            glossary_items.append({"abbreviation": abbrev, "meaning": meaning})
        
        return StructureElement(
            id="glossary",
            type="Glossary",
            title=glossary_title,
            full_text=glossary_content,
            page_range=[1],
            metadata={
                "category": "reference",
                "items_count": len(glossary_items),
                "items": glossary_items
            }
        )
    
    def _fix_truncated_content(
        self, 
        content: str, 
        full_text: str, 
        start_pos: int, 
        end_pos: int
    ) -> Tuple[str, bool]:
        """
        Check if content is truncated and attempt to fix it.
        
        Truncation indicators:
        - Content ends with comma, semicolon, colon
        - Content ends with "tại Khoản", "tại Điều" (incomplete references)
        - Content ends with "và", "hoặc", "là", "được"
        - Content ends with "như sau:", "bao gồm:" (list indicators)
        - Content doesn't end with proper sentence ending (., !, ?)
        
        Args:
            content: Current extracted content
            full_text: Full document text
            start_pos: Start position of this content in full_text
            end_pos: Current end position
            
        Returns:
            Tuple of (fixed_content, is_truncated)
        """
        # Truncation patterns - ordered by specificity
        TRUNCATION_PATTERNS = [
            # Reference patterns (most specific)
            (r'được\s+quy\s+định\s+tại\s*$', 'incomplete_reference'),
            (r'quy\s+định\s+tại\s*$', 'incomplete_reference'),
            (r'tại\s+[Kk]hoản\s+\d+\s*,?\s*$', 'incomplete_reference'),
            (r'tại\s+[Đđ]iều\s+\d+\s*,?\s*$', 'incomplete_reference'),
            (r'tại\s+[Kk]hoản\s*$', 'incomplete_reference'),
            (r'tại\s+[Đđ]iều\s*$', 'incomplete_reference'),
            (r'theo\s+[Qq]uy\s+định\s+tại\s*$', 'incomplete_reference'),
            (r'quy\s+định\s+tại\s+[Kk]hoản\s+\d+\s*,?\s*$', 'incomplete_reference'),
            (r'căn\s+cứ\s+[Kk]hoản\s*$', 'incomplete_reference'),
            (r'căn\s+cứ\s+[Đđ]iều\s*$', 'incomplete_reference'),
            (r'xem\s+[Đđ]iều\s*$', 'incomplete_reference'),
            (r'theo\s+[Đđ]iều\s*$', 'incomplete_reference'),
            
            # List indicators
            (r'như\s+sau\s*:\s*$', 'list_start'),
            (r'bao\s+gồm\s*:\s*$', 'list_start'),
            (r'sau\s+đây\s*:\s*$', 'list_start'),
            (r'các\s+trường\s+hợp\s*:\s*$', 'list_start'),
            (r'gồm\s+có\s*:\s*$', 'list_start'),
            (r'cụ\s+thể\s*:\s*$', 'list_start'),
            
            # Conjunction/connector patterns
            (r'\s+và\s*$', 'connector'),
            (r'\s+hoặc\s*$', 'connector'),
            (r'\s+hay\s*$', 'connector'),
            (r'\s+gồm\s*$', 'connector'),
            (r'\s+là\s*$', 'connector'),
            (r'\s+được\s*$', 'connector'),
            (r'\s+phải\s*$', 'connector'),
            (r'\s+của\s*$', 'connector'),
            (r'\s+cho\s*$', 'connector'),
            (r'\s+theo\s*$', 'connector'),
            (r'\s+với\s*$', 'connector'),
            (r'\s+tại\s*$', 'connector'),
            (r'\s+khi\s*$', 'connector'),
            (r'\s+nếu\s*$', 'connector'),
            (r'\s+trong\s*$', 'connector'),
            
            # Punctuation patterns
            (r',\s*$', 'punctuation'),
            (r';\s*$', 'punctuation'),
            (r':\s*$', 'punctuation'),
            (r'\.\.\.\s*$', 'ellipsis'),
        ]
        
        is_truncated = False
        truncation_type = None
        fixed_content = content
        
        # Check for truncation
        for pattern, t_type in TRUNCATION_PATTERNS:
            if re.search(pattern, content):
                is_truncated = True
                truncation_type = t_type
                logger.debug(f"Detected truncation ({t_type}) with pattern: {pattern}")
                break
        
        # Also check if content doesn't end with proper sentence ending
        if not is_truncated:
            # Check if last 100 chars contain a proper ending
            last_chars = content[-100:] if len(content) > 100 else content
            if not re.search(r'[.!?]\s*$', last_chars):
                # No proper sentence ending
                is_truncated = True
                truncation_type = 'no_ending'
                logger.debug("Detected truncation: no proper sentence ending")
        
        if is_truncated and end_pos < len(full_text):
            # Try to extend content
            remaining_text = full_text[end_pos:]
            
            # Remove page separators and headers that might be in the way
            remaining_text = re.sub(r'^-{3,}\n', '', remaining_text)
            remaining_text = re.sub(r'^Trang\s+\d+.*?\n', '', remaining_text)
            remaining_text = remaining_text.lstrip()
            
            # Don't extend if next content starts with article/chapter
            if re.match(r'^(?:Điều|CHƯƠNG)\s+\d+', remaining_text, re.IGNORECASE):
                # Next content is a new article/chapter, can't extend
                logger.debug("Cannot extend: next content is new article/chapter")
                return fixed_content, is_truncated
            
            # Find extension based on truncation type
            extension = ""
            
            if truncation_type in ('incomplete_reference', 'connector', 'punctuation'):
                # Look for sentence completion
                # Find next sentence ending that's not part of "Điều X." or "Khoản X."
                sentence_pattern = r'(?:(?<=[^0-9Đđ])[.]\s)|(?:[!?]\s)'
                
                for m in re.finditer(sentence_pattern, remaining_text):
                    potential_ext = remaining_text[:m.end()].strip()
                    
                    # Don't include if it contains another article start
                    if re.search(r'Điều\s+\d+[\.\s:：]', potential_ext):
                        # Only take content before the article
                        art_match = re.search(r'Điều\s+\d+[\.\s:：]', potential_ext)
                        potential_ext = potential_ext[:art_match.start()].strip()
                        if potential_ext:
                            extension = potential_ext
                        break
                    
                    # Good extension found
                    if len(potential_ext) < 1000:  # Max 1000 chars extension
                        extension = potential_ext
                        break
                
            elif truncation_type == 'list_start':
                # For list starters, capture the list items
                # Look for end of list (double newline or next article)
                list_end = re.search(r'\n\n(?=[A-Z])|(?=Điều\s+\d+)', remaining_text)
                if list_end and list_end.start() < 2000:
                    extension = remaining_text[:list_end.start()].strip()
            
            elif truncation_type in ('ellipsis', 'no_ending'):
                # Try to find any reasonable stopping point
                # First try sentence end
                sentence_end = re.search(r'[.!?]\s+(?=[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰ\d])', remaining_text)
                if sentence_end and sentence_end.start() < 500:
                    potential_ext = remaining_text[:sentence_end.end()].strip()
                    if not re.search(r'Điều\s+\d+', potential_ext):
                        extension = potential_ext
                
                # If no sentence end, try paragraph break
                if not extension:
                    para_end = re.search(r'\n\n', remaining_text)
                    if para_end and para_end.start() < 500:
                        potential_ext = remaining_text[:para_end.start()].strip()
                        if not re.search(r'Điều\s+\d+', potential_ext):
                            extension = potential_ext
            
            # Apply extension if found
            if extension:
                # Clean extension
                extension = self._remove_headers_footers(extension) if hasattr(self, '_remove_headers_footers') else extension
                fixed_content = content.rstrip() + " " + extension.lstrip()
                logger.info(f"✅ Extended truncated content ({truncation_type}) by {len(extension)} chars")
        
        return fixed_content, is_truncated
    
    def _extract_clauses(self, article_content: str, article_id: str) -> List[StructureElement]:
        """Extract clauses (Khoản) from article content."""
        clauses = []
        
        # Pattern for numbered clauses: 1., 2., 3. or a), b), c)
        clause_pattern = r'^(\d+)\.\s+(.+?)(?=^\d+\.|^[a-z]\)|$)'
        
        for match in re.finditer(clause_pattern, article_content, re.MULTILINE | re.DOTALL):
            clause_num = match.group(1)
            clause_content = match.group(2).strip()
            
            clause_id = f"{article_id}_khoan_{clause_num}"
            
            clause = StructureElement(
                id=clause_id,
                type="Clause",
                title=f"Khoản {clause_num}",
                full_text=clause_content[:1000],  # Limit length
                page_range=[1],
                parent_id=article_id,
                metadata={"clause_number": int(clause_num)}
            )
            clauses.append(clause)
        
        return clauses
    
    def _extract_tables(self, content: str) -> List[StructureElement]:
        """
        Extract Markdown tables from content.
        
        Enhanced: Also parses tables into JSON format for structured search.
        """
        tables = []
        
        # Markdown table pattern
        table_pattern = r'(\|[^\n]+\|\n)(\|[-:| ]+\|\n)((?:\|[^\n]+\|\n)+)'
        
        for i, match in enumerate(re.finditer(table_pattern, content)):
            table_content = match.group(0)
            
            # Try to find table title (line before table)
            pre_content = content[:match.start()]
            title_match = re.search(r'([^\n]+)\n*$', pre_content)
            table_title = title_match.group(1).strip() if title_match else f"Bảng {i+1}"
            
            # Parse table to JSON format
            json_data = self._parse_markdown_table_to_json(table_content)
            
            table = StructureElement(
                id=f"bang_{i+1}",
                type="Table",
                title=table_title[:100],
                full_text=table_content,
                page_range=[1],
                metadata={
                    "table_index": i + 1,
                    "columns": json_data.get("columns", []),
                    "rows_count": len(json_data.get("data", [])),
                    "json_data": json_data.get("data", [])  # Structured data for search
                }
            )
            tables.append(table)
        
        return tables
    
    def _parse_markdown_table_to_json(self, markdown_table: str) -> Dict[str, Any]:
        """
        Parse a Markdown table into structured JSON.
        
        Example:
            | A | B | C |
            |---|---|---|
            | 1 | 2 | 3 |
            
        Returns:
            {"columns": ["A", "B", "C"], "data": [{"A": "1", "B": "2", "C": "3"}]}
        """
        lines = markdown_table.strip().split('\n')
        
        if len(lines) < 3:
            return {"columns": [], "data": []}
        
        # Parse header row
        header_line = lines[0]
        columns = [col.strip() for col in header_line.split('|') if col.strip()]
        
        # Skip separator line (index 1)
        
        # Parse data rows
        data = []
        for line in lines[2:]:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:
                row_dict = {}
                for j, col in enumerate(columns):
                    row_dict[col] = cells[j] if j < len(cells) else ""
                data.append(row_dict)
        
        return {"columns": columns, "data": data}
    
    async def _verify_with_vlm(
        self,
        pdf_path: Path,
        result: ExtractionResult,
        llama_content: str = ""
    ) -> ExtractionResult:
        """
        Use VLM to verify and correct structure boundaries.
        
        Improved: Detects TOC/Chapter 1 location and sends relevant pages to VLM
        instead of fixed first 3 pages.
        """
        try:
            from pdf2image import convert_from_path
            import base64
            from io import BytesIO
            
            logger.info(f"🚀 Starting VLM verification with model: {self.config.vlm_model}")
            logger.info(f"   Base URL: {self.config.vlm_base_url}")
            
            # Step 1: Detect relevant pages from LlamaParse content
            relevant_pages = self._detect_relevant_pages_for_vlm(llama_content, result)
            logger.info(f"📍 Detected relevant pages for VLM: {relevant_pages}")
            
            # Step 2: Convert relevant pages
            logger.info("Converting sample pages for VLM verification...")
            all_pages = []
            
            for page_num in relevant_pages:
                try:
                    pages = convert_from_path(
                        str(pdf_path),
                        dpi=100,  # Lower DPI for verification
                        first_page=page_num,
                        last_page=page_num
                    )
                    if pages:
                        all_pages.append((page_num, pages[0]))
                except Exception as e:
                    logger.warning(f"Could not convert page {page_num}: {e}")
            
            # Encode images
            encoded_images = []
            for page_num, page in all_pages[:5]:  # Max 5 pages
                buffer = BytesIO()
                page.save(buffer, format="JPEG", quality=70)
                encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                encoded_images.append({"page": page_num, "data": encoded})
            
            # Call VLM for structure verification
            vlm_structure = await self._call_vlm_for_structure(encoded_images)
            
            # Merge VLM findings with LlamaParse results
            result = self._merge_vlm_findings(result, vlm_structure)
            
        except Exception as e:
            logger.warning(f"VLM verification failed, using LlamaParse structure only: {e}")
        
        return result
    
    def _detect_relevant_pages_for_vlm(
        self, 
        content: str, 
        result: ExtractionResult
    ) -> List[int]:
        """
        Detect which pages are most relevant for VLM structure verification.
        
        Strategy:
        1. Find TOC page (if exists)
        2. Find where Chapter 1 / CHƯƠNG I starts
        3. Include pages with chapter boundaries
        
        Returns list of page numbers (1-indexed)
        """
        relevant_pages = set()
        
        # Split content by page separators
        pages = content.split("---")
        
        # Pattern to find TOC
        toc_patterns = [
            r'MỤC\s+LỤC',
            r'NỘI\s+DUNG',
            r'Trang\s*\n.*?Chương',
        ]
        
        # Pattern to find Chapter 1
        chapter1_patterns = [
            r'CHƯƠNG\s+(?:1|I)[\.\s:：]',
            r'CHƯƠNG\s+(?:MỘT|NHẤT)',
        ]
        
        for i, page_content in enumerate(pages):
            page_num = i + 1
            
            # Check for TOC
            for pattern in toc_patterns:
                if re.search(pattern, page_content, re.IGNORECASE):
                    relevant_pages.add(page_num)
                    logger.debug(f"Found TOC on page {page_num}")
                    break
            
            # Check for Chapter 1
            for pattern in chapter1_patterns:
                if re.search(pattern, page_content, re.IGNORECASE):
                    relevant_pages.add(page_num)
                    # Also add next page in case chapter spans pages
                    if page_num + 1 <= len(pages):
                        relevant_pages.add(page_num + 1)
                    logger.debug(f"Found Chapter 1 on page {page_num}")
                    break
            
            # Check for any chapter boundary
            if re.search(r'CHƯƠNG\s+[IVXLCDM1-9]+[\.\s:：]', page_content, re.IGNORECASE):
                relevant_pages.add(page_num)
        
        # Always include first 2 pages (cover, intro)
        relevant_pages.add(1)
        relevant_pages.add(2)
        
        # If we found chapters, also include a middle page and end
        total_pages = len(pages)
        if total_pages > 5:
            relevant_pages.add(total_pages // 2)  # Middle
            relevant_pages.add(total_pages - 1)   # Near end
        
        # Sort and limit to reasonable number
        sorted_pages = sorted(relevant_pages)[:7]
        
        # If no specific pages found, fallback to first 5
        if len(sorted_pages) < 3:
            sorted_pages = list(range(1, min(6, total_pages + 1)))
        
        return sorted_pages
    
    async def _call_vlm_for_structure(self, encoded_images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call VLM API to extract document structure from images.
        
        Args:
            encoded_images: List of dicts with {"page": int, "data": base64_string}
        """
        import httpx
        
        logger.info(f"📤 Calling VLM API with {len(encoded_images)} images...")
        
        # Build page info for prompt
        page_info = ", ".join([f"trang {img['page']}" for img in encoded_images[:5]])
        
        prompt = f"""Phân tích cấu trúc văn bản pháp lý trong các trang này ({page_info}).
        
Trả về JSON với format:
{{
    "chapters": [{{"id": "chuong_X", "title": "CHƯƠNG X...", "start_page": N}}],
    "articles": [{{"id": "dieu_X", "title": "Điều X...", "page": N, "chapter_id": "chuong_X"}}],
    "table_of_contents_page": N or null
}}

Chỉ liệt kê các Chương và Điều bạn nhìn thấy rõ ràng trong các trang này.
Lưu ý: Số trang thực tế là {page_info}.
Trả về JSON hợp lệ, không có text khác."""

        # Build message content with images
        content = [{"type": "text", "text": prompt}]
        for img_data in encoded_images[:5]:  # Max 5 images
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_data['data']}",
                    "detail": "low"
                }
            })
        
        headers = {
            "Authorization": f"Bearer {self.config.vlm_api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.config.vlm_model,
            "messages": [
                {"role": "user", "content": content}
            ],
            "max_tokens": 2000,
            "temperature": 0.0
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info(f"📡 Sending request to: {self.config.vlm_base_url}/chat/completions")
            response = await client.post(
                f"{self.config.vlm_base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            content_text = result["choices"][0]["message"]["content"]
            logger.info(f"✅ VLM response received: {len(content_text)} chars")
            
            # Parse JSON from response
            try:
                # Extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', content_text)
                if json_match:
                    parsed = json.loads(json_match.group())
                    logger.info(f"📊 VLM found: {len(parsed.get('chapters', []))} chapters, "
                               f"{len(parsed.get('articles', []))} articles")
                    return parsed
            except json.JSONDecodeError:
                logger.warning(f"Could not parse VLM JSON response: {content_text[:200]}")
            
            return {}
    
    def _merge_vlm_findings(
        self,
        result: ExtractionResult,
        vlm_structure: Dict[str, Any]
    ) -> ExtractionResult:
        """Merge VLM structure verification with LlamaParse extraction.
        
        Important: Normalize all chapter IDs to Arabic numerals (chuong_1, chuong_2, etc.)
        """
        
        def normalize_chapter_id(ch_id: str) -> str:
            """Convert chapter ID to standard format with Arabic numerals."""
            match = re.search(r'chuong_([IVXLCDM]+|\d+)', ch_id, re.IGNORECASE)
            if match:
                num = match.group(1)
                if num.isdigit():
                    return f"chuong_{num}"
                else:
                    # Convert Roman to Arabic
                    arabic = self._roman_to_arabic(num.upper())
                    return f"chuong_{arabic}"
            return ch_id
        
        # Normalize VLM chapter IDs
        vlm_chapters = {}
        for ch in vlm_structure.get("chapters", []):
            normalized_id = normalize_chapter_id(ch.get("id", ""))
            vlm_chapters[normalized_id] = ch
            
        vlm_articles = {}
        for art in vlm_structure.get("articles", []):
            vlm_articles[art.get("id", "")] = art
        
        # Update chapter page ranges
        for chapter in result.chapters:
            if chapter.id in vlm_chapters:
                vlm_ch = vlm_chapters[chapter.id]
                chapter.page_range = [vlm_ch.get("start_page", 1)]
        
        # Update article page numbers and parent relationships
        for article in result.articles:
            if article.id in vlm_articles:
                vlm_art = vlm_articles[article.id]
                article.page_range = [vlm_art.get("page", 1)]
                if vlm_art.get("chapter_id"):
                    # Normalize the parent chapter ID
                    article.parent_id = normalize_chapter_id(vlm_art["chapter_id"])
        
        # Check for missing chapters detected by VLM
        # But only add if we have fewer than 6 chapters (standard for Quy che Dao tao)
        existing_chapter_ids = {c.id for c in result.chapters}
        
        # Don't add VLM chapters if we already have 6 (avoid duplicates)
        if len(result.chapters) < 6:
            for ch_id, vlm_ch in vlm_chapters.items():
                normalized_id = normalize_chapter_id(ch_id)
                if normalized_id not in existing_chapter_ids:
                    logger.info(f"Adding missing chapter from VLM: {normalized_id}")
                    result.chapters.append(StructureElement(
                        id=normalized_id,
                        type="Chapter",
                        title=vlm_ch.get("title", normalized_id),
                        full_text="",
                        page_range=[vlm_ch.get("start_page", 1)],
                        metadata={"source": "vlm_verification"}
                    ))
        else:
            logger.info(f"Skipping VLM chapters - already have {len(result.chapters)} chapters")
        
        return result


# =============================================================================
# Convenience function for pipeline integration
# =============================================================================

async def run_hybrid_pipeline(
    pdf_path: Path,
    category: str = "Quy chế Đào tạo"
) -> Dict[str, Any]:
    """
    Run hybrid LlamaParse + VLM extraction pipeline.
    
    Args:
        pdf_path: Path to PDF file
        category: Document category
        
    Returns:
        Dictionary with extraction results
    """
    extractor = HybridExtractor.from_env()
    result = await extractor.extract_from_pdf(pdf_path, category)
    return result.to_dict()
