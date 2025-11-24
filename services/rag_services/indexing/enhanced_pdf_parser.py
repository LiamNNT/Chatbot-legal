"""
Enhanced PDF Parser with Table Extraction
==========================================

Replaces PyPDF2 with pdfplumber for better handling of:
- Tables and structured data
- Multi-column layouts
- Complex formatting

Key improvements:
1. Extract tables separately from text
2. Preserve table structure (rows/columns)
3. Better text extraction from complex layouts
4. Support for both linear text and tabular data

Usage:
    ```python
    from indexing.enhanced_pdf_parser import EnhancedPDFParser
    
    parser = EnhancedPDFParser()
    result = parser.extract_from_pdf("data/qd_790_2022.pdf")
    
    print(f"Extracted {len(result.pages)} pages")
    print(f"Found {len(result.tables)} tables")
    ```
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)


@dataclass
class TableData:
    """Represents an extracted table"""
    page_number: int
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    raw_data: List[List[Optional[str]]] = field(default_factory=list)
    caption: Optional[str] = None
    position_y: Optional[float] = None  # Y-coordinate on page (for position detection)
    table_index: int = 0  # Index of table on page (0, 1, 2, ...)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "page_number": self.page_number,
            "headers": self.headers,
            "rows": self.rows,
            "caption": self.caption,
            "row_count": len(self.rows),
            "col_count": len(self.headers)
        }
    
    def to_markdown(self) -> str:
        """Convert table to markdown format"""
        if not self.headers:
            return ""
        
        lines = []
        
        # Caption
        if self.caption:
            lines.append(f"**{self.caption}**\n")
        
        # Headers
        lines.append("| " + " | ".join(self.headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(self.headers)) + " |")
        
        # Rows
        for row in self.rows:
            # Pad row if needed
            padded_row = row + [""] * (len(self.headers) - len(row))
            lines.append("| " + " | ".join(str(cell) for cell in padded_row) + " |")
        
        return "\n".join(lines)
    
    def to_text(self) -> str:
        """Convert table to plain text"""
        lines = []
        
        if self.caption:
            lines.append(f"BẢNG: {self.caption}")
        
        # Headers
        if self.headers:
            lines.append(" | ".join(self.headers))
            lines.append("-" * 60)
        
        # Rows
        for row in self.rows:
            lines.append(" | ".join(str(cell) for cell in row))
        
        return "\n".join(lines)


@dataclass
class PageContent:
    """Content extracted from a single page"""
    page_number: int
    text: str
    tables: List[TableData] = field(default_factory=list)
    has_tables: bool = False
    table_positions: List[Optional[float]] = field(default_factory=list)  # Y-coordinates of tables
    
    def get_full_text(self, include_tables: bool = True, inject_at_position: bool = True) -> str:
        """
        Get combined text with optional table content
        
        Args:
            include_tables: Whether to include table content
            inject_at_position: If True, try to inject tables at their original position
                               If False, append tables at the end (old behavior)
        """
        if not include_tables or not self.tables:
            return self.text
        
        # Option 1: Inject tables at approximate position (RECOMMENDED)
        if inject_at_position:
            return self._inject_tables_at_position()
        
        # Option 2: Append tables at end (old behavior)
        else:
            parts = [self.text]
            parts.append("\n\n--- BẢNG BIỂU ---\n")
            for i, table in enumerate(self.tables, 1):
                parts.append(f"\nBảng {i} (trang {self.page_number}):")
                parts.append(table.to_text())
                parts.append("")
            return "\n".join(parts)
    
    def _inject_tables_at_position(self) -> str:
        """
        Inject tables into text at approximate positions
        
        Strategy:
        - Detect table markers in text: "bảng dưới đây", "theo bảng", "như sau:"
        - Insert table markdown right after these markers
        - If no marker found, append at end
        """
        if not self.tables:
            return self.text
        
        text = self.text
        lines = text.split('\n')
        
        # Common table reference patterns in Vietnamese legal docs
        table_markers = [
            r'bảng\s+dưới\s+đây',
            r'theo\s+bảng',
            r'như\s+sau\s*:',
            r'quy\s+định\s+tại\s+bảng',
            r'chi\s+tiết\s+như\s+sau',
        ]
        
        import re
        
        # Find insertion points for each table
        inserted_tables = set()
        result_lines = []
        
        for line_idx, line in enumerate(lines):
            result_lines.append(line)
            
            # Check if this line contains a table marker
            for table_idx, table in enumerate(self.tables):
                if table_idx in inserted_tables:
                    continue
                
                # Check if line matches any marker pattern
                for pattern in table_markers:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Insert table after this line
                        result_lines.append(f"\n[Bảng {table_idx + 1}]")
                        result_lines.append(table.to_markdown())
                        result_lines.append("")
                        inserted_tables.add(table_idx)
                        break
        
        # Append any tables that weren't inserted
        if len(inserted_tables) < len(self.tables):
            result_lines.append("\n--- BẢNG BIỂU ---")
            for table_idx, table in enumerate(self.tables):
                if table_idx not in inserted_tables:
                    result_lines.append(f"\n[Bảng {table_idx + 1} - trang {self.page_number}]")
                    result_lines.append(table.to_markdown())
        
        return '\n'.join(result_lines)


@dataclass
class PDFExtractionResult:
    """Result of PDF extraction"""
    pages: List[PageContent] = field(default_factory=list)
    tables: List[TableData] = field(default_factory=list)
    total_pages: int = 0
    total_tables: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_full_text(self, include_tables: bool = True) -> str:
        """Get all text from all pages"""
        return "\n\n".join(
            page.get_full_text(include_tables) 
            for page in self.pages
        )
    
    def get_tables_by_page(self, page_number: int) -> List[TableData]:
        """Get all tables from a specific page"""
        return [t for t in self.tables if t.page_number == page_number]


class EnhancedPDFParser:
    """
    Enhanced PDF parser using pdfplumber
    
    Features:
    - Better text extraction (handles multi-column, complex layouts)
    - Table detection and extraction
    - Preserves table structure
    - Separates linear text from tabular data
    """
    
    def __init__(self, extract_tables: bool = True, table_settings: Optional[Dict] = None):
        """
        Initialize parser
        
        Args:
            extract_tables: Whether to extract tables
            table_settings: Custom settings for table extraction
        """
        self.extract_tables = extract_tables
        self.table_settings = table_settings or {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "min_words_vertical": 3,
            "min_words_horizontal": 1,
        }
    
    def extract_from_pdf(self, pdf_path: Path) -> PDFExtractionResult:
        """
        Extract text and tables from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            PDFExtractionResult with pages, text, and tables
        """
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber not installed. Install with: pip install pdfplumber")
            raise ImportError(
                "pdfplumber required for enhanced PDF parsing. "
                "Install with: pip install pdfplumber"
            )
        
        result = PDFExtractionResult()
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                result.total_pages = len(pdf.pages)
                result.metadata = pdf.metadata or {}
                
                logger.info(f"Processing {result.total_pages} pages from {pdf_path.name}")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_content = self._extract_page_content(page, page_num)
                    result.pages.append(page_content)
                    
                    if page_content.tables:
                        result.tables.extend(page_content.tables)
                
                result.total_tables = len(result.tables)
                
                logger.info(
                    f"Extracted {result.total_pages} pages, "
                    f"{result.total_tables} tables from {pdf_path.name}"
                )
        
        except Exception as e:
            logger.error(f"Failed to parse PDF {pdf_path}: {e}")
            raise
        
        return result
    
    def _extract_page_content(self, page, page_num: int) -> PageContent:
        """Extract content from a single page with table position detection"""
        # Extract text
        text = page.extract_text() or ""
        
        # Extract tables with position info
        tables = []
        table_positions = []  # Track where tables appear in the page
        
        if self.extract_tables:
            try:
                # Get tables with bounding boxes
                raw_tables = page.extract_tables(self.table_settings)
                page_tables_objs = page.find_tables(self.table_settings)
                
                for i, (raw_table, table_obj) in enumerate(zip(raw_tables, page_tables_objs)):
                    if raw_table and len(raw_table) > 0:
                        table = self._process_table(raw_table, page_num, i)
                        if table:
                            # Store table position (top y-coordinate)
                            table.position_y = table_obj.bbox[1] if hasattr(table_obj, 'bbox') else None
                            tables.append(table)
                            table_positions.append(table.position_y)
            except Exception as e:
                logger.warning(f"Failed to extract tables from page {page_num}: {e}")
        
        return PageContent(
            page_number=page_num,
            text=text,
            tables=tables,
            has_tables=len(tables) > 0,
            table_positions=table_positions
        )
    
    def _process_table(self, raw_table: List[List[Optional[str]]], page_num: int, table_idx: int = 0) -> Optional[TableData]:
        """Process raw table data into structured format"""
        if not raw_table or len(raw_table) < 2:
            return None
        
        # First row as headers
        headers = [str(cell).strip() if cell else "" for cell in raw_table[0]]
        
        # Remaining rows as data
        rows = []
        for row in raw_table[1:]:
            cleaned_row = [str(cell).strip() if cell else "" for cell in row]
            # Skip empty rows
            if any(cleaned_row):
                rows.append(cleaned_row)
        
        if not rows:
            return None
        
        # Try to detect caption (look for text before table)
        caption = None
        # This would require more context from the page
        
        return TableData(
            page_number=page_num,
            headers=headers,
            rows=rows,
            raw_data=raw_table,
            caption=caption,
            table_index=table_idx
        )
    
    def extract_tables_only(self, pdf_path: Path) -> List[TableData]:
        """Extract only tables from PDF"""
        result = self.extract_from_pdf(pdf_path)
        return result.tables
    
    def extract_text_only(self, pdf_path: Path) -> str:
        """Extract only text from PDF (no tables)"""
        result = self.extract_from_pdf(pdf_path)
        return result.get_full_text(include_tables=False)


# ============================================================================
# Integration with existing ETL pipeline
# ============================================================================

class EnhancedPDFLoader:
    """
    Drop-in replacement for PyPDF2-based PDF loader
    Compatible with existing DocumentLoader interface
    """
    
    def __init__(self, extract_tables: bool = True):
        self.parser = EnhancedPDFParser(extract_tables=extract_tables)
    
    def can_load(self, file_path: Path) -> bool:
        """Check if file is a PDF"""
        return file_path.suffix.lower() == '.pdf'
    
    async def load(self, file_path: Path) -> Optional[str]:
        """
        Load PDF and return text (compatible with existing interface)
        
        Tables are converted to text format and included in output
        """
        try:
            result = self.parser.extract_from_pdf(file_path)
            return result.get_full_text(include_tables=True)
        except Exception as e:
            logger.error(f"Failed to load PDF {file_path}: {e}")
            return None
    
    async def load_with_tables(self, file_path: Path) -> Optional[PDFExtractionResult]:
        """
        Load PDF and return structured result with separate tables
        
        Use this for advanced processing where you need table structure
        """
        try:
            return self.parser.extract_from_pdf(file_path)
        except Exception as e:
            logger.error(f"Failed to load PDF {file_path}: {e}")
            return None


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def demo():
        # Example 1: Simple text extraction
        loader = EnhancedPDFLoader()
        text = await loader.load(Path("data/qd_790_2022.pdf"))
        print(f"Extracted {len(text)} characters")
        
        # Example 2: Extract with table structure
        result = await loader.load_with_tables(Path("data/qd_790_2022.pdf"))
        if result:
            print(f"\nFound {result.total_tables} tables:")
            for table in result.tables:
                print(f"  - Page {table.page_number}: {len(table.rows)} rows")
                print(f"    Headers: {', '.join(table.headers)}")
        
        # Example 3: Export table to markdown
        if result and result.tables:
            first_table = result.tables[0]
            print("\nFirst table in markdown:")
            print(first_table.to_markdown())
    
    asyncio.run(demo())
