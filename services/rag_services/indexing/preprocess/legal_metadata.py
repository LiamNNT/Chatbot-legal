"""
Enhanced Document Metadata for Knowledge Graph Support

Extends DocumentMetadata with legal structure fields for KG building.
"""

from core.domain.models import DocumentMetadata
from typing import Optional, Dict, Any


class LegalDocumentMetadata(DocumentMetadata):
    """
    Extended metadata for legal documents.
    
    Adds fields necessary for Knowledge Graph construction:
    - chapter/article/clause hierarchy
    - document classification
    - entity references
    """
    
    # Legal structure (for KG hierarchy)
    chapter: Optional[str] = None           # "Chương I", "Chương II"
    chapter_title: Optional[str] = None     # "Những quy định chung"
    article: Optional[str] = None           # "Điều 1", "Điều 2"
    article_title: Optional[str] = None     # "Phạm vi điều chỉnh"
    clause: Optional[str] = None            # "Khoản 1", "Khoản 2"
    point: Optional[str] = None             # "Điểm a", "Điểm b"
    
    # Document classification (for KG node type)
    doc_number: Optional[str] = None        # "790/QĐ-ĐHCNTT"
    issue_date: Optional[str] = None        # "28/9/2022"
    issuer: Optional[str] = None            # "Hiệu trưởng"
    status: Optional[str] = None            # "hiệu lực", "hết hiệu lực"
    
    # Entity extraction hints (for KG population)
    mentioned_entities: Optional[Dict[str, Any]] = None  # {"courses": [...], "requirements": [...]}
    
    # KG-specific IDs
    kg_node_id: Optional[str] = None        # Unique ID for graph node
    kg_parent_id: Optional[str] = None      # Parent node ID
    
    def to_kg_properties(self) -> Dict[str, Any]:
        """
        Convert to Knowledge Graph node properties.
        
        Returns:
            Dict suitable for GraphNode creation
        """
        return {
            # Core properties
            'doc_id': self.doc_id,
            'chunk_id': self.chunk_id,
            'title': self.title,
            
            # Legal structure
            'chapter': self.chapter,
            'chapter_title': self.chapter_title,
            'article': self.article,
            'article_title': self.article_title,
            'clause': self.clause,
            'point': self.point,
            
            # Document metadata
            'doc_number': self.doc_number,
            'issue_date': self.issue_date,
            'year': self.year,
            'issuer': self.issuer,
            'status': self.status or 'hiệu lực',
            
            # Classification
            'doc_type': self.doc_type,
            'subject': self.subject,
            'faculty': self.faculty,
            
            # Source tracking
            'page': self.page,
            'language': self.language.value if self.language else 'vi',
            
            # Extra metadata
            **self.extra
        }
    
    def get_kg_node_type(self) -> str:
        """
        Determine KG node type based on structure level.
        
        Returns:
            Node type for graph (QUY_DINH, CATEGORY, etc.)
        """
        if self.article:
            return "QUY_DINH"  # Each Điều is a regulation node
        elif self.chapter:
            return "CATEGORY"  # Chapter is a category
        else:
            return "DOCUMENT"  # Document level
    
    def get_hierarchical_path(self) -> str:
        """
        Get hierarchical path for this element.
        
        Returns:
            Path like "Chương I > Điều 1 > Khoản 2"
        """
        parts = []
        
        if self.chapter:
            parts.append(self.chapter)
        if self.article:
            parts.append(self.article)
        if self.clause:
            parts.append(self.clause)
        if self.point:
            parts.append(self.point)
        
        return " > ".join(parts) if parts else self.doc_id


def create_legal_chunk_metadata(
    doc_id: str,
    chunk_index: int,
    legal_element: 'LegalElement',
    doc_metadata: Dict,
    doc_title: str = ""
) -> LegalDocumentMetadata:
    """
    Create metadata for a legal document chunk.
    
    Args:
        doc_id: Document ID
        chunk_index: Chunk index
        legal_element: Parsed legal structure element
        doc_metadata: Document-level metadata
        doc_title: Document title
        
    Returns:
        LegalDocumentMetadata instance
    """
    from indexing.preprocess.legal_structure_parser import StructureType
    from core.domain.models import DocumentLanguage
    
    chunk_id = f"{doc_id}_article_{legal_element.metadata.get('article_number', chunk_index)}"
    
    # Determine structure fields
    chapter = legal_element.metadata.get('chapter')
    chapter_title = legal_element.metadata.get('chapter_title')
    article = legal_element.id if legal_element.type == StructureType.ARTICLE else None
    article_title = legal_element.title if legal_element.type == StructureType.ARTICLE else None
    
    metadata = LegalDocumentMetadata(
        # Core fields
        doc_id=doc_id,
        chunk_id=chunk_id,
        title=doc_title or doc_metadata.get('title', ''),
        page=chunk_index + 1,  # Approximate
        
        # Legal structure
        chapter=chapter,
        chapter_title=chapter_title,
        article=article,
        article_title=article_title,
        
        # Document metadata
        doc_type='regulation',
        doc_number=doc_metadata.get('doc_number'),
        issue_date=doc_metadata.get('issue_date'),
        year=doc_metadata.get('year'),
        issuer=doc_metadata.get('issuer'),
        subject=doc_metadata.get('subject'),
        faculty='UIT',
        language=DocumentLanguage.VIETNAMESE,
        
        # Sections (for backward compatibility)
        section=chapter or f"article_{chunk_index}",
        subsection=article or f"chunk_{chunk_index}",
        
        # KG IDs
        kg_node_id=chunk_id,
        kg_parent_id=chapter if chapter else doc_id,
        
        # Extra
        extra={
            'structure_type': legal_element.type.value,
            'level': legal_element.level,
            'content_length': len(legal_element.content),
            'has_parent': legal_element.parent_id is not None,
            'parent_id': legal_element.parent_id,
            'children_count': len(legal_element.children_ids),
        }
    )
    
    return metadata
