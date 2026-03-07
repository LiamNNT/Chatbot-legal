"""
Graph domain models for Legal Knowledge Graph.

This module defines domain models for graph entities aligned with
the Vietnamese Legal Document schema (Luật, Nghị định, Điều, Khoản, etc.)

Schema Source: knowledge_graph_schema.py
Domain: Pháp luật Quốc gia (National Law)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from enum import Enum
import uuid
import json


# =============================================================================
# ENUMS - Định nghĩa các loại giá trị cố định
# =============================================================================

class NodeType(str, Enum):
    """
    Các loại Node trong đồ thị tri thức pháp luật.
    
    Node types are defined with Vietnamese values for Neo4j labels,
    maintaining compatibility with the knowledge_graph_schema.py.
    """
    # --- Văn bản pháp luật ---
    LUAT = "Luật"                           # Luật do Quốc hội ban hành
    NGHI_DINH = "Nghị định"                 # Nghị định của Chính phủ
    THONG_TU = "Thông tư"                   # Thông tư của Bộ
    QUYET_DINH = "Quyết định"               # Quyết định
    
    # --- Cấu trúc văn bản ---
    PHAN = "Phần"                           # Phần (Part)
    CHUONG = "Chương"                       # Chương (Chapter)
    MUC = "Mục"                             # Mục (Section)
    DIEU = "Điều"                           # Điều (Article)
    KHOAN = "Khoản"                         # Khoản (Clause)
    DIEM = "Điểm"                           # Điểm (Point)
    
    # --- Thực thể pháp lý ---
    CO_QUAN = "Cơ quan"                     # Cơ quan nhà nước
    TO_CHUC = "Tổ chức"                     # Tổ chức
    CA_NHAN = "Cá nhân"                     # Cá nhân/Công dân
    CHU_THE = "Chủ thể"                     # Chủ thể pháp luật chung
    
    # --- Khái niệm pháp lý ---
    KHAI_NIEM = "Khái niệm"                 # Định nghĩa/Khái niệm
    THUAT_NGU = "Thuật ngữ"                 # Thuật ngữ chuyên ngành
    NGUYEN_TAC = "Nguyên tắc"               # Nguyên tắc pháp lý
    CHINH_SACH = "Chính sách"               # Chính sách nhà nước
    
    # --- Quyền và nghĩa vụ ---
    QUYEN = "Quyền"                         # Quyền
    NGHIA_VU = "Nghĩa vụ"                   # Nghĩa vụ
    TRACH_NHIEM = "Trách nhiệm"             # Trách nhiệm
    
    # --- Hành vi ---
    HANH_VI_CAM = "Hành vi cấm"             # Hành vi bị nghiêm cấm
    HANH_VI_PHEP = "Hành vi được phép"      # Hành vi được phép
    VI_PHAM = "Vi phạm"                     # Vi phạm pháp luật
    
    # --- Chế tài ---
    CHE_TAI = "Chế tài"                     # Chế tài/Hình phạt
    XU_LY = "Xử lý"                         # Biện pháp xử lý
    
    # --- Thủ tục ---
    THU_TUC = "Thủ tục"                     # Thủ tục hành chính
    DIEU_KIEN = "Điều kiện"                 # Điều kiện
    TRINH_TU = "Trình tự"                   # Trình tự thực hiện
    
    # --- Đối tượng điều chỉnh ---
    LINH_VUC = "Lĩnh vực"                   # Lĩnh vực điều chỉnh
    PHAM_VI = "Phạm vi"                     # Phạm vi áp dụng


class EdgeType(str, Enum):
    """
    Các loại quan hệ (Edge) trong đồ thị tri thức pháp luật.
    
    IMPORTANT: Values are UPPER_SNAKE_CASE ASCII for Neo4j compatibility.
    Neo4j queries use these values as relationship types (e.g., [:THUOC_VE]).
    """
    # --- Quan hệ cấu trúc văn bản ---
    THUOC_VE = "THUOC_VE"                   # Điều thuộc về Chương (belongs to)
    KE_TIEP = "KE_TIEP"                     # Điều 2 kế tiếp Điều 1 (next)
    
    # --- Quan hệ tham chiếu ---
    THAM_CHIEU = "THAM_CHIEU"               # Điều A tham chiếu Điều B
    DAN_CHIEU = "DAN_CHIEU"                 # Dẫn chiếu đến văn bản khác
    VIEN_DAN = "VIEN_DAN"                   # Viện dẫn căn cứ
    
    # --- Quan hệ thời gian/hiệu lực ---
    THAY_THE = "THAY_THE"                   # Luật mới thay thế luật cũ
    SUA_DOI = "SUA_DOI"                     # Sửa đổi điều khoản
    BO_SUNG = "BO_SUNG"                     # Bổ sung điều khoản
    BAI_BO = "BAI_BO"                       # Bãi bỏ điều khoản
    
    # --- Quan hệ ngữ nghĩa ---
    DINH_NGHIA = "DINH_NGHIA"               # Định nghĩa khái niệm
    LA_LOAI = "LA_LOAI"                     # Quan hệ phân loại (is-a)
    BAO_GOM = "BAO_GOM"                     # Bao gồm (has-part)
    LIEN_QUAN = "LIEN_QUAN"                 # Liên quan đến
    DONG_NGHIA = "DONG_NGHIA"               # Đồng nghĩa/tương đương
    
    # --- Quan hệ pháp lý ---
    QUY_DINH = "QUY_DINH"                   # Quy định về
    AP_DUNG = "AP_DUNG"                     # Áp dụng cho
    DIEU_CHINH = "DIEU_CHINH"               # Điều chỉnh đối tượng
    RANG_BUOC = "RANG_BUOC"                 # Ràng buộc pháp lý
    
    # --- Quan hệ chủ thể ---
    CO_QUYEN = "CO_QUYEN"                   # Chủ thể có quyền
    CO_NGHIA_VU = "CO_NGHIA_VU"             # Chủ thể có nghĩa vụ
    CHIU_TRACH_NHIEM = "CHIU_TRACH_NHIEM"   # Chịu trách nhiệm
    QUAN_LY = "QUAN_LY"                     # Cơ quan quản lý
    THUOC_THAM_QUYEN = "THUOC_THAM_QUYEN"   # Thuộc thẩm quyền
    
    # --- Quan hệ hành vi - chế tài ---
    DAN_DEN = "DAN_DEN"                     # Hành vi dẫn đến hậu quả
    BI_XU_LY = "BI_XU_LY"                   # Hành vi bị xử lý
    
    # --- Quan hệ điều kiện ---
    YEU_CAU = "YEU_CAU"                     # Yêu cầu điều kiện
    NGOAI_TRU = "NGOAI_TRU"                 # Ngoại trừ trường hợp


class LegalStatus(str, Enum):
    """Trạng thái hiệu lực của văn bản/điều khoản"""
    CON_HIEU_LUC = "Còn hiệu lực"
    HET_HIEU_LUC = "Hết hiệu lực"
    CHUA_CO_HIEU_LUC = "Chưa có hiệu lực"
    BI_SUA_DOI = "Bị sửa đổi"
    BI_BAI_BO = "Bị bãi bỏ"


class IssuingAuthority(str, Enum):
    """Cơ quan ban hành văn bản"""
    QUOC_HOI = "Quốc hội"
    UY_BAN_THUONG_VU_QH = "Ủy ban Thường vụ Quốc hội"
    CHU_TICH_NUOC = "Chủ tịch nước"
    CHINH_PHU = "Chính phủ"
    THU_TUONG = "Thủ tướng Chính phủ"
    BO = "Bộ"
    CO_QUAN_NGANG_BO = "Cơ quan ngang Bộ"


# =============================================================================
# BASE NODE CLASS
# =============================================================================

@dataclass
class GraphNode:
    """
    Domain model for a graph node.
    
    Attributes:
        id: Unique identifier (UUID, generated if not provided)
        node_type: Node type from NodeType enum
        name: Display name/title
        content: Full content text
        properties: Additional node properties as dict
        keywords: Keywords for search
        embedding: Vector embedding for semantic search
        metadata: Additional metadata
    """
    node_type: NodeType
    properties: Dict[str, Any]
    id: Optional[str] = None
    name: str = ""
    content: str = ""
    keywords: List[str] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate node properties and generate ID if needed"""
        if self.id is None:
            self.id = str(uuid.uuid4())
        self._validate_properties()
    
    def _validate_properties(self):
        """
        Validate that required properties are present based on node type.
        """
        required_props = self._get_required_properties()
        for prop in required_props:
            if prop not in self.properties and not getattr(self, prop, None):
                # Log warning but don't raise to allow flexibility during extraction
                pass
    
    def _get_required_properties(self) -> List[str]:
        """Get required properties for this node type"""
        requirements = {
            # Document types
            NodeType.LUAT: ["document_number", "title"],
            NodeType.NGHI_DINH: ["document_number", "title"],
            NodeType.THONG_TU: ["document_number", "title"],
            NodeType.QUYET_DINH: ["document_number", "title"],
            
            # Structure types
            NodeType.CHUONG: ["chapter_number"],
            NodeType.MUC: ["section_number"],
            NodeType.DIEU: ["article_number"],
            NodeType.KHOAN: ["clause_number"],
            NodeType.DIEM: ["point_label"],
            
            # Semantic types
            NodeType.KHAI_NIEM: ["term", "definition"],
            NodeType.HANH_VI_CAM: ["prohibited_act"],
            NodeType.CHE_TAI: ["sanction_content"],
            NodeType.QUYEN: ["right_content"],
            NodeType.NGHIA_VU: ["obligation_content"],
            NodeType.THU_TUC: ["procedure_name"],
            
            # Entity types
            NodeType.CHU_THE: ["subject_type"],
            NodeType.CO_QUAN: ["name"],
            NodeType.TO_CHUC: ["name"],
        }
        return requirements.get(self.node_type, [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "node_type": self.node_type.value if self.node_type else None,
            "name": self.name,
            "content": self.content,
            "keywords": self.keywords,
            "properties": self.properties,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class GraphRelationship:
    """
    Domain model for a graph relationship (edge).
    
    Attributes:
        source_id: ID of source node
        target_id: ID of target node
        edge_type: Relationship type from EdgeType enum
        properties: Relationship properties
        weight: Relationship strength/weight
        description: Human-readable description
        source_reference: Source reference (e.g., specific article)
        effective_date: When this relationship became effective
    """
    source_id: str
    target_id: str
    edge_type: EdgeType
    properties: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    weight: float = 1.0
    description: str = ""
    source_reference: str = ""
    effective_date: Optional[date] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value if self.edge_type else None,
            "properties": self.properties,
            "weight": self.weight,
            "description": self.description,
            "source_reference": self.source_reference,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None
        }
    
    def to_json(self) -> str:
        """Convert to JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class GraphPath:
    """
    Domain model for a path in the graph.
    """
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    length: int = field(init=False)
    
    def __post_init__(self):
        self.length = len(self.relationships)
    
    def get_node_ids(self) -> List[str]:
        """Get list of node IDs in the path"""
        return [node.id for node in self.nodes if node.id]
    
    def get_relationship_types(self) -> List[str]:
        """Get list of relationship types in the path"""
        return [rel.edge_type.value for rel in self.relationships]


@dataclass
class SubGraph:
    """
    Domain model for a subgraph.
    """
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    center_node_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_node_count(self) -> int:
        return len(self.nodes)
    
    def get_relationship_count(self) -> int:
        return len(self.relationships)
    
    def get_node_types(self) -> List[str]:
        return list(set(node.node_type.value for node in self.nodes if node.node_type))


@dataclass
class GraphQuery:
    """
    Domain model for graph queries.
    """
    query_type: str  # e.g., "traverse", "shortest_path", "subgraph", "legal_trace"
    start_node_id: Optional[str] = None
    end_node_id: Optional[str] = None
    relationship_types: List[EdgeType] = field(default_factory=list)
    max_depth: int = 2
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 10


# =============================================================================
# QUERY INTENT - For routing legal queries
# =============================================================================

class QueryIntent(str, Enum):
    """
    Legal Query Intent Categories for Router Agent.
    """
    # Tra cứu cấu trúc văn bản
    TRA_CUU_DIEU = "tra_cuu_dieu"           # Tra cứu nội dung điều luật
    TRA_CUU_VAN_BAN = "tra_cuu_van_ban"     # Tra cứu văn bản pháp luật
    
    # Tra cứu quan hệ pháp lý
    HANH_VI_CAM = "hanh_vi_cam"             # Hỏi về hành vi bị cấm
    CHE_TAI = "che_tai"                     # Hỏi về chế tài xử phạt
    QUYEN_NGHIA_VU = "quyen_nghia_vu"       # Hỏi về quyền và nghĩa vụ
    
    # Tra cứu khái niệm
    GIAI_THICH_TU_NGU = "giai_thich_tu_ngu" # Giải thích thuật ngữ
    KHAI_NIEM = "khai_niem"                 # Tra cứu định nghĩa
    
    # Tra cứu liên kết
    LIEN_KET_VAN_BAN = "lien_ket_van_ban"   # Tìm văn bản liên quan
    LICH_SU_SUA_DOI = "lich_su_sua_doi"     # Lịch sử sửa đổi văn bản
    
    # General
    GENERAL = "general"


@dataclass
class RoutingDecision:
    """
    Routing decision made by Router Agent.
    """
    intent: QueryIntent
    confidence: float
    route_to: str  # "graph_traversal", "vector_search", "hybrid_search", "legal_trace"
    extracted_entities: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: Optional[str] = None
    
    def should_use_graph(self) -> bool:
        return self.route_to in ["graph_traversal", "legal_trace", "hybrid_search"]
    
    def should_use_vector(self) -> bool:
        return self.route_to in ["vector_search", "hybrid_search"]


# =============================================================================
# ENTITY AND RELATION EXTRACTION MODELS
# =============================================================================

@dataclass
class Entity:
    """
    Extracted entity from legal text.
    """
    text: str
    type: str  # Should match NodeType values
    start: int
    end: int
    confidence: float = 1.0
    normalized: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "type": self.type,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "normalized": self.normalized,
            "metadata": self.metadata
        }


@dataclass
class Relation:
    """
    Extracted relation from legal text.
    """
    source: Entity
    target: Entity
    rel_type: str  # Should match EdgeType values
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "rel_type": self.rel_type,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


# =============================================================================
# SPECIALIZED LEGAL NODE MODELS
# =============================================================================

@dataclass
class LegalDocumentNode(GraphNode):
    """
    Node for Legal Document (Luật, Nghị định, Thông tư...)
    """
    document_number: str = ""               # Số hiệu: "20/2023/QH15"
    document_type: str = ""                 # Loại văn bản: "Luật"
    title: str = ""                         # Tên văn bản
    issuing_authority: Optional[IssuingAuthority] = None
    issuing_date: Optional[date] = None
    effective_date: Optional[date] = None
    signer: str = ""
    status: LegalStatus = LegalStatus.CON_HIEU_LUC
    legal_basis: List[str] = field(default_factory=list)
    scope: str = ""
    subjects: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.properties:
            self.properties = {}
        self.properties.update({
            "document_number": self.document_number,
            "document_type": self.document_type,
            "title": self.title,
            "issuing_date": self.issuing_date.isoformat() if self.issuing_date else None,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "status": self.status.value if self.status else None,
        })
        super().__post_init__()


@dataclass
class ArticleNode(GraphNode):
    """
    Node for Article (Điều luật)
    """
    article_number: int = 0
    article_title: str = ""
    article_content: str = ""
    parent_document_id: str = ""
    parent_chapter_id: str = ""
    parent_section_id: str = ""
    article_category: str = ""              # "định nghĩa", "quy định", "chế tài"
    order_index: int = 0
    is_definition_article: bool = False
    
    def __post_init__(self):
        if not self.properties:
            self.properties = {}
        self.properties.update({
            "article_number": self.article_number,
            "article_title": self.article_title,
            "parent_document_id": self.parent_document_id,
            "article_category": self.article_category,
            "is_definition_article": self.is_definition_article,
        })
        self.node_type = NodeType.DIEU
        super().__post_init__()


@dataclass
class ClauseNode(GraphNode):
    """
    Node for Clause (Khoản trong Điều)
    """
    clause_number: int = 0
    clause_content: str = ""
    parent_article_id: str = ""
    order_index: int = 0
    
    def __post_init__(self):
        if not self.properties:
            self.properties = {}
        self.properties.update({
            "clause_number": self.clause_number,
            "clause_content": self.clause_content,
            "parent_article_id": self.parent_article_id,
        })
        self.node_type = NodeType.KHOAN
        super().__post_init__()


@dataclass
class ConceptNode(GraphNode):
    """
    Node for Legal Concept/Definition (Khái niệm pháp lý)
    """
    term: str = ""
    definition: str = ""
    source_article_id: str = ""
    source_document_id: str = ""
    related_terms: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.properties:
            self.properties = {}
        self.properties.update({
            "term": self.term,
            "definition": self.definition,
            "source_article_id": self.source_article_id,
            "source_document_id": self.source_document_id,
        })
        self.node_type = NodeType.KHAI_NIEM
        super().__post_init__()


@dataclass
class ProhibitedActNode(GraphNode):
    """
    Node for Prohibited Act (Hành vi bị cấm)
    """
    prohibited_act: str = ""
    source_article_id: str = ""
    related_sanctions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.properties:
            self.properties = {}
        self.properties.update({
            "prohibited_act": self.prohibited_act,
            "source_article_id": self.source_article_id,
        })
        self.node_type = NodeType.HANH_VI_CAM
        super().__post_init__()


@dataclass
class SanctionNode(GraphNode):
    """
    Node for Sanction (Chế tài/Hình phạt)
    """
    sanction_type: str = ""
    sanction_content: str = ""
    applicable_violations: List[str] = field(default_factory=list)
    source_article_id: str = ""
    
    def __post_init__(self):
        if not self.properties:
            self.properties = {}
        self.properties.update({
            "sanction_type": self.sanction_type,
            "sanction_content": self.sanction_content,
            "source_article_id": self.source_article_id,
        })
        self.node_type = NodeType.CHE_TAI
        super().__post_init__()


# =============================================================================
# HELPER FUNCTIONS - Creating common node types
# =============================================================================

def create_legal_document_node(
    document_number: str,
    title: str,
    document_type: str = "Luật",
    issuing_authority: IssuingAuthority = None,
    issuing_date: date = None,
    effective_date: date = None,
    status: LegalStatus = LegalStatus.CON_HIEU_LUC,
    **kwargs
) -> GraphNode:
    """Create a Legal Document node"""
    properties = {
        "document_number": document_number,
        "title": title,
        "document_type": document_type,
        "issuing_authority": issuing_authority.value if issuing_authority else None,
        "issuing_date": issuing_date.isoformat() if issuing_date else None,
        "effective_date": effective_date.isoformat() if effective_date else None,
        "status": status.value,
        **kwargs
    }
    
    node_type_map = {
        "Luật": NodeType.LUAT,
        "Nghị định": NodeType.NGHI_DINH,
        "Thông tư": NodeType.THONG_TU,
        "Quyết định": NodeType.QUYET_DINH,
    }
    
    return GraphNode(
        node_type=node_type_map.get(document_type, NodeType.LUAT),
        properties=properties,
        name=title
    )


def create_article_node(
    article_number: int,
    article_title: str,
    article_content: str,
    parent_document_id: str,
    parent_chapter_id: str = "",
    is_definition_article: bool = False,
    **kwargs
) -> GraphNode:
    """Create an Article (Điều) node"""
    properties = {
        "article_number": article_number,
        "article_title": article_title,
        "article_content": article_content,
        "parent_document_id": parent_document_id,
        "parent_chapter_id": parent_chapter_id,
        "is_definition_article": is_definition_article,
        **kwargs
    }
    return GraphNode(
        node_type=NodeType.DIEU,
        properties=properties,
        name=f"Điều {article_number}. {article_title}",
        content=article_content
    )


def create_clause_node(
    clause_number: int,
    clause_content: str,
    parent_article_id: str,
    **kwargs
) -> GraphNode:
    """Create a Clause (Khoản) node"""
    properties = {
        "clause_number": clause_number,
        "clause_content": clause_content,
        "parent_article_id": parent_article_id,
        **kwargs
    }
    return GraphNode(
        node_type=NodeType.KHOAN,
        properties=properties,
        name=f"Khoản {clause_number}",
        content=clause_content
    )


def create_concept_node(
    term: str,
    definition: str,
    source_article_id: str,
    source_document_id: str = "",
    **kwargs
) -> GraphNode:
    """Create a Concept (Khái niệm) node"""
    properties = {
        "term": term,
        "definition": definition,
        "source_article_id": source_article_id,
        "source_document_id": source_document_id,
        **kwargs
    }
    return GraphNode(
        node_type=NodeType.KHAI_NIEM,
        properties=properties,
        name=term,
        content=definition
    )


def create_prohibited_act_node(
    prohibited_act: str,
    source_article_id: str,
    related_sanctions: List[str] = None,
    **kwargs
) -> GraphNode:
    """Create a Prohibited Act (Hành vi cấm) node"""
    properties = {
        "prohibited_act": prohibited_act,
        "source_article_id": source_article_id,
        "related_sanctions": related_sanctions or [],
        **kwargs
    }
    return GraphNode(
        node_type=NodeType.HANH_VI_CAM,
        properties=properties,
        name=prohibited_act[:100],  # Truncate for display name
        content=prohibited_act
    )


def create_sanction_node(
    sanction_type: str,
    sanction_content: str,
    source_article_id: str,
    applicable_violations: List[str] = None,
    **kwargs
) -> GraphNode:
    """Create a Sanction (Chế tài) node"""
    properties = {
        "sanction_type": sanction_type,
        "sanction_content": sanction_content,
        "source_article_id": source_article_id,
        "applicable_violations": applicable_violations or [],
        **kwargs
    }
    return GraphNode(
        node_type=NodeType.CHE_TAI,
        properties=properties,
        name=sanction_type,
        content=sanction_content
    )


def create_structural_relationship(
    child_id: str,
    parent_id: str,
    description: str = ""
) -> GraphRelationship:
    """Create a THUOC_VE (belongs to) structural relationship"""
    return GraphRelationship(
        source_id=child_id,
        target_id=parent_id,
        edge_type=EdgeType.THUOC_VE,
        description=description
    )


def create_definition_relationship(
    article_id: str,
    concept_id: str,
    description: str = ""
) -> GraphRelationship:
    """Create a DINH_NGHIA (defines) relationship"""
    return GraphRelationship(
        source_id=article_id,
        target_id=concept_id,
        edge_type=EdgeType.DINH_NGHIA,
        description=description
    )


def create_sanction_relationship(
    violation_id: str,
    sanction_id: str,
    description: str = ""
) -> GraphRelationship:
    """Create a BI_XU_LY (sanctioned by) relationship"""
    return GraphRelationship(
        source_id=violation_id,
        target_id=sanction_id,
        edge_type=EdgeType.BI_XU_LY,
        description=description
    )


def create_amendment_relationship(
    new_document_id: str,
    old_document_id: str,
    amendment_type: str = "sửa đổi",
    effective_date: date = None,
    description: str = ""
) -> GraphRelationship:
    """Create an amendment/replacement relationship between documents"""
    edge_type_map = {
        "thay thế": EdgeType.THAY_THE,
        "sửa đổi": EdgeType.SUA_DOI,
        "bổ sung": EdgeType.BO_SUNG,
        "bãi bỏ": EdgeType.BAI_BO,
    }
    
    return GraphRelationship(
        source_id=new_document_id,
        target_id=old_document_id,
        edge_type=edge_type_map.get(amendment_type, EdgeType.SUA_DOI),
        effective_date=effective_date,
        description=description
    )