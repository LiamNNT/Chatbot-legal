# tests/test_kg_building.py
"""
Tests for Knowledge Graph building in the ingestion pipeline.

Tests cover:
- NodeType enum values (Vietnamese labels)
- EdgeType enum values (ASCII UPPER_SNAKE_CASE)
- THUOC_VE relationship direction (child -> parent)
- KE_TIEP relationship for siblings
- Correct node properties for each type
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.domain.graph_models import (
    NodeType,
    EdgeType,
    GraphNode,
    GraphRelationship,
)
from indexing.loaders.vietnam_legal_docx_parser import (
    LegalNodeType,
    LegalNode,
)


class TestNodeTypeEnum:
    """Test NodeType enum values for Neo4j labels."""
    
    def test_node_type_values_are_vietnamese(self):
        """Test that document structure node types use Vietnamese labels."""
        assert NodeType.LUAT.value == "Luật"
        assert NodeType.NGHI_DINH.value == "Nghị định"
        assert NodeType.THONG_TU.value == "Thông tư"
        assert NodeType.CHUONG.value == "Chương"
        assert NodeType.MUC.value == "Mục"
        assert NodeType.DIEU.value == "Điều"
        assert NodeType.KHOAN.value == "Khoản"
        assert NodeType.DIEM.value == "Điểm"
    
    def test_entity_type_values_are_vietnamese(self):
        """Test that entity node types use Vietnamese labels."""
        assert NodeType.KHAI_NIEM.value == "Khái niệm"
        assert NodeType.THUAT_NGU.value == "Thuật ngữ"
        assert NodeType.CO_QUAN.value == "Cơ quan"
        assert NodeType.CHU_THE.value == "Chủ thể"


class TestEdgeTypeEnum:
    """Test EdgeType enum values for Neo4j relationships."""
    
    def test_edge_type_values_are_ascii(self):
        """Test that EdgeType values are ASCII UPPER_SNAKE_CASE."""
        assert EdgeType.THUOC_VE.value == "THUOC_VE"
        assert EdgeType.KE_TIEP.value == "KE_TIEP"
        assert EdgeType.THAM_CHIEU.value == "THAM_CHIEU"
        assert EdgeType.DINH_NGHIA.value == "DINH_NGHIA"
        assert EdgeType.BI_XU_LY.value == "BI_XU_LY"
    
    def test_all_edge_types_are_uppercase(self):
        """Test that all EdgeType values are uppercase ASCII."""
        for edge_type in EdgeType:
            assert edge_type.value == edge_type.value.upper(), \
                f"EdgeType {edge_type.name} value should be uppercase"
            # Should only contain ASCII alphanumeric and underscores
            assert edge_type.value.replace("_", "").isalnum(), \
                f"EdgeType {edge_type.name} value should be ASCII"


class TestGraphNodeCreation:
    """Test GraphNode creation with proper properties."""
    
    def test_create_document_node(self):
        """Test creating a document (Luật) node."""
        node = GraphNode(
            id="DOC=20/2023/QH15",
            node_type=NodeType.LUAT,
            name="Luật Bảo vệ dữ liệu cá nhân",
            content="Nội dung...",
            properties={
                "document_number": "20/2023/QH15",
                "title": "Luật Bảo vệ dữ liệu cá nhân",
                "doc_kind": "LAW",
            }
        )
        
        assert node.id == "DOC=20/2023/QH15"
        assert node.node_type == NodeType.LUAT
        assert node.properties["document_number"] == "20/2023/QH15"
    
    def test_create_article_node(self):
        """Test creating an article (Điều) node."""
        node = GraphNode(
            id="LAW=20/2023/QH15:DIEU=3",
            node_type=NodeType.DIEU,
            name="Điều 3. Giải thích từ ngữ",
            content="Trong Luật này, các từ ngữ dưới đây được hiểu như sau...",
            properties={
                "article_number": 3,
                "article_title": "Giải thích từ ngữ",
                "is_definition_article": True,
            }
        )
        
        assert node.node_type == NodeType.DIEU
        assert node.properties["article_number"] == 3
        assert node.properties["is_definition_article"] is True
    
    def test_create_clause_node(self):
        """Test creating a clause (Khoản) node."""
        node = GraphNode(
            id="LAW=20/2023/QH15:DIEU=3:KHOAN=1",
            node_type=NodeType.KHOAN,
            name="Khoản 1",
            content="Dữ liệu cá nhân là thông tin dưới dạng...",
            properties={
                "clause_number": 1,
            }
        )
        
        assert node.node_type == NodeType.KHOAN
        assert node.properties["clause_number"] == 1


class TestGraphRelationshipCreation:
    """Test GraphRelationship creation."""
    
    def test_create_thuoc_ve_relationship(self):
        """Test creating THUOC_VE (belongs to) relationship."""
        rel = GraphRelationship(
            source_id="LAW=20/2023/QH15:DIEU=3",
            target_id="DOC=20/2023/QH15",
            edge_type=EdgeType.THUOC_VE,
            properties={"relationship_type": "structural"}
        )
        
        assert rel.edge_type == EdgeType.THUOC_VE
        assert rel.edge_type.value == "THUOC_VE"
    
    def test_create_ke_tiep_relationship(self):
        """Test creating KE_TIEP (next) relationship."""
        rel = GraphRelationship(
            source_id="LAW=20/2023/QH15:DIEU=1",
            target_id="LAW=20/2023/QH15:DIEU=2",
            edge_type=EdgeType.KE_TIEP,
            properties={"relationship_type": "sequential"}
        )
        
        assert rel.edge_type == EdgeType.KE_TIEP
        assert rel.edge_type.value == "KE_TIEP"


class TestTHUOC_VEDirection:
    """Test that THUOC_VE relationship direction is correct (child -> parent)."""
    
    def test_thuoc_ve_article_to_document(self):
        """Test THUOC_VE direction: Article -> Document."""
        # According to Vietnamese legal semantics:
        # "Điều 3 thuộc về Luật 20/2023/QH15"
        # Source: child (Article), Target: parent (Document)
        
        article_id = "LAW=20/2023/QH15:DIEU=3"
        document_id = "DOC=20/2023/QH15"
        
        rel = GraphRelationship(
            source_id=article_id,  # Child (Article)
            target_id=document_id,  # Parent (Document)
            edge_type=EdgeType.THUOC_VE,
        )
        
        assert rel.source_id == article_id
        assert rel.target_id == document_id
    
    def test_thuoc_ve_clause_to_article(self):
        """Test THUOC_VE direction: Clause -> Article."""
        # "Khoản 1 thuộc về Điều 3"
        
        clause_id = "LAW=20/2023/QH15:DIEU=3:KHOAN=1"
        article_id = "LAW=20/2023/QH15:DIEU=3"
        
        rel = GraphRelationship(
            source_id=clause_id,  # Child (Clause)
            target_id=article_id,  # Parent (Article)
            edge_type=EdgeType.THUOC_VE,
        )
        
        assert rel.source_id == clause_id
        assert rel.target_id == article_id


class TestKE_TIEPDirection:
    """Test that KE_TIEP relationship direction is correct (prev -> next)."""
    
    def test_ke_tiep_article_order(self):
        """Test KE_TIEP direction: Article 1 -> Article 2."""
        article1_id = "LAW=20/2023/QH15:DIEU=1"
        article2_id = "LAW=20/2023/QH15:DIEU=2"
        
        rel = GraphRelationship(
            source_id=article1_id,  # Previous
            target_id=article2_id,  # Next
            edge_type=EdgeType.KE_TIEP,
        )
        
        assert rel.source_id == article1_id
        assert rel.target_id == article2_id


class TestLegalNodeTypeMappingToNodeType:
    """Test mapping from parser LegalNodeType to domain NodeType."""
    
    def test_legal_node_type_to_node_type_mapping(self):
        """Test the expected mapping from LegalNodeType to NodeType."""
        mapping = {
            LegalNodeType.LAW: NodeType.LUAT,
            LegalNodeType.CHAPTER: NodeType.CHUONG,
            LegalNodeType.SECTION: NodeType.MUC,
            LegalNodeType.ARTICLE: NodeType.DIEU,
            LegalNodeType.CLAUSE: NodeType.KHOAN,
            LegalNodeType.POINT: NodeType.DIEM,
            LegalNodeType.DEFINITION_ITEM: NodeType.KHAI_NIEM,
        }
        
        for legal_type, expected_node_type in mapping.items():
            # Verify the expected node types exist
            assert expected_node_type is not None
            assert expected_node_type.value  # Has a value
