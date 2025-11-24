"""
Legal Structure Parser for Vietnamese Regulations

Parses Vietnamese legal documents (Quy chế, Quy định) into structured format:
- Chương (Chapter)
- Điều (Article)
- Khoản (Clause)
- Điểm (Point)

CRITICAL for Knowledge Graph:
- Each Điều becomes a QUY_DINH node
- Each Chương becomes a CATEGORY node
- Relationships: (Điều)-[:THUOC_CHUONG]->(Chương)
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class StructureType(str, Enum):
    """Legal structure hierarchy."""
    DOCUMENT = "document"        # Toàn bộ văn bản
    CHAPTER = "chapter"          # Chương
    ARTICLE = "article"          # Điều
    CLAUSE = "clause"            # Khoản
    POINT = "point"              # Điểm
    SECTION = "section"          # Mục (nếu có)


@dataclass
class LegalElement:
    """
    Represents a legal structural element.
    
    Maps directly to Knowledge Graph nodes:
    - type=ARTICLE → QUY_DINH node
    - type=CHAPTER → CATEGORY node
    """
    type: StructureType
    id: str                      # e.g., "Điều 1", "Chương II"
    title: str                   # e.g., "Phạm vi điều chỉnh"
    content: str                 # Full text content
    start_pos: int               # Character position in original text
    end_pos: int                 # Character position in original text
    
    # Hierarchical relationships (for KG)
    parent_id: Optional[str] = None      # e.g., Điều 1 → parent = "Chương I"
    children_ids: List[str] = field(default_factory=list)
    
    # Metadata for chunking
    level: int = 0               # 0=document, 1=chapter, 2=article, 3=clause
    
    # KG-ready metadata
    metadata: Dict = field(default_factory=dict)
    
    def to_kg_node_properties(self) -> Dict:
        """
        Convert to Knowledge Graph node properties.
        
        Returns:
            Dict ready for GraphNode creation
        """
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'type': self.type.value,
            'level': self.level,
            'parent': self.parent_id,
            **self.metadata
        }


class LegalStructureParser:
    """
    Parse Vietnamese legal documents into structured hierarchy.
    
    Supports:
    - Roman numeral chapters (CHƯƠNG I, II, III...)
    - Arabic numeral chapters (Chương 1, 2, 3...)
    - Articles (Điều 1, 2, 3...)
    - Clauses (1., 2., 3... or a), b), c)...)
    - Points (a), b), c)... or a., b., c....)
    """
    
    # Regex patterns for Vietnamese legal documents
    CHAPTER_PATTERNS = [
        # CHƯƠNG I, II, III (Roman numerals)
        r'(?:CHƯƠNG|Chương)\s+([IVXLCDM]+)[\s:\.]+([^\n]{3,100})',
        # Chương 1, 2, 3 (Arabic numerals)
        r'(?:CHƯƠNG|Chương)\s+(\d+)[\s:\.]+([^\n]{3,100})',
    ]
    
    ARTICLE_PATTERNS = [
        # Điều 1, Điều 2, ...
        r'(?:ĐIỀU|Điều)\s+(\d+)[\s:\.]+([^\n]{3,150})',
    ]
    
    CLAUSE_PATTERNS = [
        # 1., 2., 3. or 1) 2) 3)
        r'\n(\d+)[\.\)]\s+([^\n]{10,500})',
    ]
    
    POINT_PATTERNS = [
        # a), b), c) or a., b., c.
        r'\n([a-zđ])[\.\)]\s+([^\n]{5,300})',
    ]
    
    def __init__(self):
        self.elements: List[LegalElement] = []
    
    def parse(self, text: str) -> List[LegalElement]:
        """
        Parse legal document into structured elements.
        
        Args:
            text: Cleaned text from PDF
            
        Returns:
            List of LegalElement sorted by position
        """
        self.elements = []
        
        # Parse in hierarchical order
        chapters = self._parse_chapters(text)
        articles = self._parse_articles(text)
        
        # Build hierarchy
        self._build_hierarchy(chapters, articles)
        
        # Sort by position
        all_elements = chapters + articles
        all_elements.sort(key=lambda x: x.start_pos)
        
        self.elements = all_elements
        return self.elements
    
    def _parse_chapters(self, text: str) -> List[LegalElement]:
        """Parse chapters (Chương)."""
        chapters = []
        
        for pattern in self.CHAPTER_PATTERNS:
            for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                chapter_num = match.group(1)
                chapter_title = match.group(2).strip()
                
                # Normalize ID
                if chapter_num.isdigit():
                    chapter_id = f"Chương {chapter_num}"
                else:
                    chapter_id = f"Chương {chapter_num}"
                
                # Find content boundaries
                start_pos = match.start()
                
                # Content ends at next chapter or end of document
                next_chapter = self._find_next_chapter(text, start_pos)
                end_pos = next_chapter if next_chapter else len(text)
                
                content = text[start_pos:end_pos].strip()
                
                element = LegalElement(
                    type=StructureType.CHAPTER,
                    id=chapter_id,
                    title=chapter_title,
                    content=content,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    level=1,
                    metadata={
                        'chapter_number': chapter_num,
                        'chapter_type': 'roman' if not chapter_num.isdigit() else 'arabic'
                    }
                )
                
                chapters.append(element)
        
        return chapters
    
    def _parse_articles(self, text: str) -> List[LegalElement]:
        """Parse articles (Điều)."""
        articles = []
        
        for pattern in self.ARTICLE_PATTERNS:
            for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                article_num = match.group(1)
                article_title = match.group(2).strip()
                
                article_id = f"Điều {article_num}"
                
                # Find content boundaries
                start_pos = match.start()
                
                # Content ends at next article or chapter
                next_article = self._find_next_article(text, start_pos)
                end_pos = next_article if next_article else len(text)
                
                content = text[start_pos:end_pos].strip()
                
                element = LegalElement(
                    type=StructureType.ARTICLE,
                    id=article_id,
                    title=article_title,
                    content=content,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    level=2,
                    metadata={
                        'article_number': int(article_num),
                    }
                )
                
                articles.append(element)
        
        return articles
    
    def _build_hierarchy(self, chapters: List[LegalElement], articles: List[LegalElement]):
        """Build parent-child relationships."""
        # Map articles to chapters
        for article in articles:
            # Find which chapter this article belongs to
            containing_chapter = None
            
            for chapter in chapters:
                if chapter.start_pos <= article.start_pos < chapter.end_pos:
                    containing_chapter = chapter
                    break
            
            if containing_chapter:
                article.parent_id = containing_chapter.id
                containing_chapter.children_ids.append(article.id)
                article.metadata['chapter'] = containing_chapter.id
                article.metadata['chapter_title'] = containing_chapter.title
    
    def _find_next_chapter(self, text: str, current_pos: int) -> Optional[int]:
        """Find start position of next chapter."""
        for pattern in self.CHAPTER_PATTERNS:
            match = re.search(pattern, text[current_pos + 1:], re.MULTILINE | re.IGNORECASE)
            if match:
                return current_pos + 1 + match.start()
        return None
    
    def _find_next_article(self, text: str, current_pos: int) -> Optional[int]:
        """Find start position of next article."""
        for pattern in self.ARTICLE_PATTERNS:
            match = re.search(pattern, text[current_pos + 1:], re.MULTILINE | re.IGNORECASE)
            if match:
                return current_pos + 1 + match.start()
        return None
    
    def get_articles(self) -> List[LegalElement]:
        """Get only articles (for chunking)."""
        return [e for e in self.elements if e.type == StructureType.ARTICLE]
    
    def get_chapters(self) -> List[LegalElement]:
        """Get only chapters."""
        return [e for e in self.elements if e.type == StructureType.CHAPTER]
    
    def get_hierarchy_summary(self) -> Dict:
        """
        Get document structure summary.
        
        Useful for debugging and validation.
        """
        chapters = self.get_chapters()
        articles = self.get_articles()
        
        summary = {
            'total_chapters': len(chapters),
            'total_articles': len(articles),
            'chapters': []
        }
        
        for chapter in chapters:
            chapter_articles = [
                a for a in articles
                if a.parent_id == chapter.id
            ]
            
            summary['chapters'].append({
                'id': chapter.id,
                'title': chapter.title,
                'articles_count': len(chapter_articles),
                'articles': [
                    {'id': a.id, 'title': a.title}
                    for a in chapter_articles
                ]
            })
        
        return summary


def extract_document_metadata(text: str) -> Dict:
    """
    Extract document-level metadata.
    
    For Knowledge Graph document node properties.
    """
    metadata = {
        'title': None,
        'doc_number': None,
        'issue_date': None,
        'issuer': None,
        'subject': None,
    }
    
    # Extract title (usually at the top, all caps)
    title_patterns = [
        r'(QUY\s+CHẾ\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]{10,150})',
        r'(QUY\s+ĐỊNH\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]{10,150})',
        r'(QUYẾT\s+ĐỊNH\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]{10,150})',
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metadata['title'] = match.group(1).strip()
            metadata['subject'] = match.group(1).strip()
            break
    
    # Extract document number
    doc_num_patterns = [
        r'Số[\s:]+(\d+/[\d\-A-Z]+)',
        r'Quyết định số[\s:]+(\d+/[\d\-A-Z]+)',
        r'(\d+)/QĐ-ĐHCNTT',
    ]
    
    for pattern in doc_num_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metadata['doc_number'] = match.group(1)
            break
    
    # Extract issue date
    date_patterns = [
        r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            day, month, year = match.groups()
            metadata['issue_date'] = f"{day}/{month}/{year}"
            metadata['year'] = int(year)
            break
    
    # Extract issuer
    issuer_patterns = [
        r'(HIỆU TRƯỞNG|GIÁM ĐỐC|CHỦ TỊCH)',
    ]
    
    for pattern in issuer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metadata['issuer'] = match.group(1)
            break
    
    return metadata


# Demo and testing
if __name__ == "__main__":
    # Sample legal text
    sample_text = """
    QUY CHẾ ĐÀO TẠO THEO HỌC CHẾ TÍN CHỈ
    
    CHƯƠNG I: NHỮNG QUY ĐỊNH CHUNG
    
    Điều 1: Phạm vi điều chỉnh
    
    Quy chế này quy định về đào tạo theo học chế tín chỉ tại Trường Đại học
    Công nghệ Thông tin, Đại học Quốc gia TP.HCM.
    
    Điều 2: Đối tượng áp dụng
    
    1. Sinh viên đại học chính quy
    2. Sinh viên liên thông
    3. Cán bộ giảng viên
    
    CHƯƠNG II: ĐIỀU KIỆN ĐĂNG KÝ HỌC PHẦN
    
    Điều 3: Điều kiện chung
    
    Sinh viên được đăng ký học phần khi đáp ứng các điều kiện sau:
    a) Đã hoàn thành các học phần tiên quyết
    b) Có đủ điều kiện về học lực
    
    Điều 4: Số tín chỉ tối đa
    
    Sinh viên không được đăng ký quá 24 tín chỉ trong một học kỳ.
    """
    
    print("=" * 80)
    print("LEGAL STRUCTURE PARSER - DEMO")
    print("=" * 80)
    print()
    
    # Parse structure
    parser = LegalStructureParser()
    elements = parser.parse(sample_text)
    
    print(f"📊 Parsed {len(elements)} elements")
    print()
    
    # Show hierarchy
    summary = parser.get_hierarchy_summary()
    print("📋 Document Structure:")
    print(f"  Total Chapters: {summary['total_chapters']}")
    print(f"  Total Articles: {summary['total_articles']}")
    print()
    
    for chapter in summary['chapters']:
        print(f"  {chapter['id']}: {chapter['title']}")
        print(f"    Articles: {chapter['articles_count']}")
        for article in chapter['articles']:
            print(f"      - {article['id']}: {article['title']}")
        print()
    
    # Show KG-ready properties
    print("🔗 Knowledge Graph Node Properties:")
    print()
    for element in elements[:4]:  # Show first 4
        print(f"  {element.id}:")
        props = element.to_kg_node_properties()
        for key, value in props.items():
            if key != 'content':  # Skip content for brevity
                print(f"    {key}: {value}")
        print()
    
    # Extract metadata
    print("📄 Document Metadata:")
    metadata = extract_document_metadata(sample_text)
    for key, value in metadata.items():
        if value:
            print(f"  {key}: {value}")
