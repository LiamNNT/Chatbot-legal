# app/core/retrieval/metadata_filter_builder.py
"""
Metadata Filter Builder for Vector Database Queries.

This module builds database-specific filters from LegalQuery metadata.
Supports both Weaviate and OpenSearch filter formats.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from app.search.retrieval.schemas import LegalQuery

logger = logging.getLogger(__name__)


class MetadataFilterBuilder(ABC):
    """
    Abstract base class for metadata filter builders.
    
    Each database has its own filter format, so we use the Strategy pattern
    to allow different implementations.
    """
    
    @abstractmethod
    def build_filter(
        self,
        legal_query: LegalQuery,
        strict: bool = False,
        additional_filters: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Build database-specific filter from LegalQuery.
        
        Args:
            legal_query: Parsed legal query with metadata
            strict: If True, use exact match; if False, use partial/fuzzy match
            additional_filters: Extra filters to include
            
        Returns:
            Database-specific filter object
        """
        pass
    
    @abstractmethod
    def build_filter_from_dict(
        self,
        filters: Dict[str, Any],
        strict: bool = False,
    ) -> Any:
        """
        Build database-specific filter from dictionary.
        
        Args:
            filters: Dictionary of field -> value filters
            strict: If True, use exact match
            
        Returns:
            Database-specific filter object
        """
        pass
    
    @abstractmethod
    def build_chunk_id_filter(self, chunk_ids: List[str]) -> Any:
        """
        Build filter to retrieve specific chunks by ID.
        
        Args:
            chunk_ids: List of chunk IDs to retrieve
            
        Returns:
            Database-specific filter object
        """
        pass


class WeaviateFilterBuilder(MetadataFilterBuilder):
    """
    Filter builder for Weaviate vector database.
    
    Weaviate uses a Where clause with operators like:
    - Equal, NotEqual
    - ContainsAny, ContainsAll
    - Like (for text matching)
    - And, Or (for combining filters)
    """
    
    # Mapping of metadata fields to Weaviate property names
    FIELD_MAPPING = {
        "law_id": "law_id",
        "article_id": "article_id",
        "clause_no": "clause_no", 
        "point_no": "point_no",
        "chapter": "chapter",
        "section": "section",
        "doc_type": "doc_type",
        "source_file": "filename",
    }
    
    def build_filter(
        self,
        legal_query: LegalQuery,
        strict: bool = False,
        additional_filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Build Weaviate Where filter from LegalQuery."""
        
        conditions = []
        
        # Build conditions from legal query
        if legal_query.law_id:
            conditions.append(
                self._build_condition("law_id", legal_query.law_id, strict)
            )
        
        if legal_query.article_id:
            # Article ID might be stored as "Điều 11" or just "11"
            article_value = legal_query.article_id
            if not article_value.startswith("Điều"):
                # Try both formats
                conditions.append({
                    "operator": "Or",
                    "operands": [
                        self._build_condition("article_id", article_value, strict),
                        self._build_condition("article_id", f"Điều {article_value}", strict),
                    ]
                })
            else:
                conditions.append(
                    self._build_condition("article_id", article_value, strict)
                )
        
        if legal_query.clause_no:
            conditions.append(
                self._build_condition("clause_no", legal_query.clause_no, strict)
            )
        
        if legal_query.point_no:
            conditions.append(
                self._build_condition("point_no", legal_query.point_no.lower(), strict)
            )
        
        # Add additional filters
        if additional_filters:
            for field, value in additional_filters.items():
                if value is not None:
                    conditions.append(
                        self._build_condition(field, value, strict)
                    )
        
        # Combine conditions
        if not conditions:
            return None
        
        if len(conditions) == 1:
            return conditions[0]
        
        return {
            "operator": "And",
            "operands": conditions,
        }
    
    def build_filter_from_dict(
        self,
        filters: Dict[str, Any],
        strict: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Build Weaviate Where filter from dictionary."""
        
        conditions = []
        
        for field, value in filters.items():
            if value is not None:
                mapped_field = self.FIELD_MAPPING.get(field, field)
                conditions.append(
                    self._build_condition(mapped_field, value, strict)
                )
        
        if not conditions:
            return None
        
        if len(conditions) == 1:
            return conditions[0]
        
        return {
            "operator": "And",
            "operands": conditions,
        }
    
    def build_chunk_id_filter(self, chunk_ids: List[str]) -> Dict[str, Any]:
        """Build filter to retrieve specific chunks by ID."""
        
        if len(chunk_ids) == 1:
            return {
                "path": ["chunk_id"],
                "operator": "Equal",
                "valueText": chunk_ids[0],
            }
        
        return {
            "path": ["chunk_id"],
            "operator": "ContainsAny",
            "valueTextArray": chunk_ids,
        }
    
    def _build_condition(
        self,
        field: str,
        value: Any,
        strict: bool,
    ) -> Dict[str, Any]:
        """Build a single Weaviate filter condition."""
        
        mapped_field = self.FIELD_MAPPING.get(field, field)
        
        if isinstance(value, str):
            if strict:
                return {
                    "path": [mapped_field],
                    "operator": "Equal",
                    "valueText": value,
                }
            else:
                # Use Like for partial matching
                return {
                    "path": [mapped_field],
                    "operator": "Like",
                    "valueText": f"*{value}*",
                }
        
        elif isinstance(value, int):
            return {
                "path": [mapped_field],
                "operator": "Equal",
                "valueInt": value,
            }
        
        elif isinstance(value, float):
            return {
                "path": [mapped_field],
                "operator": "Equal",
                "valueNumber": value,
            }
        
        elif isinstance(value, bool):
            return {
                "path": [mapped_field],
                "operator": "Equal",
                "valueBoolean": value,
            }
        
        elif isinstance(value, list):
            return {
                "path": [mapped_field],
                "operator": "ContainsAny",
                "valueTextArray": [str(v) for v in value],
            }
        
        else:
            return {
                "path": [mapped_field],
                "operator": "Equal",
                "valueText": str(value),
            }


class OpenSearchFilterBuilder(MetadataFilterBuilder):
    """
    Filter builder for OpenSearch/Elasticsearch.
    
    OpenSearch uses Query DSL with:
    - term: Exact match
    - match: Full-text match
    - bool: Combining queries
    - terms: Match any of multiple values
    """
    
    # Mapping of metadata fields to OpenSearch field names
    FIELD_MAPPING = {
        "law_id": "metadata.law_id",
        "article_id": "metadata.article_id",
        "clause_no": "metadata.clause_no",
        "point_no": "metadata.point_no",
        "chapter": "metadata.chapter",
        "section": "metadata.section",
        "doc_type": "metadata.doc_type",
        "source_file": "metadata.filename",
        "chunk_id": "chunk_id",
    }
    
    def build_filter(
        self,
        legal_query: LegalQuery,
        strict: bool = False,
        additional_filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Build OpenSearch query filter from LegalQuery."""
        
        must_conditions = []
        should_conditions = []
        
        # Build conditions from legal query
        if legal_query.law_id:
            must_conditions.append(
                self._build_condition("law_id", legal_query.law_id, strict)
            )
        
        if legal_query.article_id:
            article_value = legal_query.article_id
            if not article_value.startswith("Điều"):
                # Try both formats using should with minimum_should_match
                should_conditions.append(
                    self._build_condition("article_id", article_value, strict)
                )
                should_conditions.append(
                    self._build_condition("article_id", f"Điều {article_value}", strict)
                )
            else:
                must_conditions.append(
                    self._build_condition("article_id", article_value, strict)
                )
        
        if legal_query.clause_no:
            must_conditions.append(
                self._build_condition("clause_no", legal_query.clause_no, strict)
            )
        
        if legal_query.point_no:
            must_conditions.append(
                self._build_condition("point_no", legal_query.point_no.lower(), strict)
            )
        
        # Add additional filters
        if additional_filters:
            for field, value in additional_filters.items():
                if value is not None:
                    must_conditions.append(
                        self._build_condition(field, value, strict)
                    )
        
        # Build bool query
        if not must_conditions and not should_conditions:
            return None
        
        bool_query: Dict[str, Any] = {}
        
        if must_conditions:
            bool_query["must"] = must_conditions
        
        if should_conditions:
            bool_query["should"] = should_conditions
            bool_query["minimum_should_match"] = 1
        
        return {"bool": bool_query}
    
    def build_filter_from_dict(
        self,
        filters: Dict[str, Any],
        strict: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Build OpenSearch query filter from dictionary."""
        
        must_conditions = []
        
        for field, value in filters.items():
            if value is not None:
                must_conditions.append(
                    self._build_condition(field, value, strict)
                )
        
        if not must_conditions:
            return None
        
        return {
            "bool": {
                "must": must_conditions,
            }
        }
    
    def build_chunk_id_filter(self, chunk_ids: List[str]) -> Dict[str, Any]:
        """Build filter to retrieve specific chunks by ID."""
        
        if len(chunk_ids) == 1:
            return {
                "term": {
                    "chunk_id": chunk_ids[0]
                }
            }
        
        return {
            "terms": {
                "chunk_id": chunk_ids
            }
        }
    
    def _build_condition(
        self,
        field: str,
        value: Any,
        strict: bool,
    ) -> Dict[str, Any]:
        """Build a single OpenSearch query condition."""
        
        mapped_field = self.FIELD_MAPPING.get(field, f"metadata.{field}")
        
        if isinstance(value, str):
            if strict:
                return {"term": {mapped_field: value}}
            else:
                return {"match": {mapped_field: value}}
        
        elif isinstance(value, (int, float)):
            return {"term": {mapped_field: value}}
        
        elif isinstance(value, bool):
            return {"term": {mapped_field: value}}
        
        elif isinstance(value, list):
            return {"terms": {mapped_field: [str(v) for v in value]}}
        
        else:
            return {"term": {mapped_field: str(value)}}


def get_filter_builder(backend: str) -> MetadataFilterBuilder:
    """
    Factory function to get appropriate filter builder.
    
    Args:
        backend: "weaviate" or "opensearch"
        
    Returns:
        MetadataFilterBuilder instance
    """
    builders = {
        "weaviate": WeaviateFilterBuilder,
        "opensearch": OpenSearchFilterBuilder,
        "elasticsearch": OpenSearchFilterBuilder,
    }
    
    builder_class = builders.get(backend.lower())
    if builder_class is None:
        raise ValueError(f"Unknown backend: {backend}. Supported: {list(builders.keys())}")
    
    return builder_class()
