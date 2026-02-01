# app/core/retrieval/legal_query_parser.py
"""
Legal Query Parser for Vietnamese Legal Documents.

This module parses user queries to extract legal references:
- Law IDs: "20/2023/QH15", "Luật Giáo dục đại học"
- Articles: "Điều 11", "Điều 11a"
- Clauses: "Khoản 2", "Khoản 2 Điều 11"
- Points: "Điểm a", "Điểm đ Khoản 2 Điều 11"

The parser also classifies query intent:
- LOOKUP_EXACT: Direct lookup of specific provision
- LOOKUP_ARTICLE: Lookup entire article
- SEMANTIC_QUESTION: General question requiring semantic search
- DEFINITION: Looking for term definitions
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.core.retrieval.schemas import LegalQuery, QueryIntent

logger = logging.getLogger(__name__)


# =============================================================================
# Regex Patterns for Vietnamese Legal References
# =============================================================================

# Law ID patterns
# Matches: "20/2023/QH15", "20-2023-QH15", "số 20/2023/QH15"
LAW_ID_PATTERNS = [
    # Standard format: number/year/issuer
    re.compile(
        r"(?:số\s*)?(\d+)\s*[/\-]\s*(\d{4})\s*[/\-]?\s*(QH\d*|NĐ[-\s]?CP|TT[-\s]?[A-Z]*|BLDTBXH)?",
        re.IGNORECASE | re.UNICODE
    ),
    # Named law pattern: "Luật Giáo dục đại học", "Luật Doanh nghiệp"
    re.compile(
        r"Luật\s+([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[a-zà-ỹA-ZÀ-Ỹ]+)*)",
        re.UNICODE
    ),
]

# Article patterns
# Matches: "Điều 11", "điều 11a", "Điều số 11"
ARTICLE_PATTERNS = [
    re.compile(
        r"[Đđ]iều\s+(?:số\s+)?(\d+[a-zA-ZÀ-ỹ]*)",
        re.UNICODE
    ),
]

# Clause patterns  
# Matches: "Khoản 2", "khoản 2 Điều 11", "K.2"
CLAUSE_PATTERNS = [
    re.compile(
        r"[Kk]hoản\s+(\d+)",
        re.UNICODE
    ),
    re.compile(
        r"[Kk]\.?\s*(\d+)(?=\s*[Đđ]iều|\s*$)",
        re.UNICODE
    ),
]

# Point patterns
# Matches: "Điểm a", "điểm đ", "Điểm a) Khoản 2"
POINT_PATTERNS = [
    re.compile(
        r"[Đđ]iểm\s+([a-zđ])",
        re.UNICODE | re.IGNORECASE
    ),
]

# Definition patterns - Only match when asking "what is X" without legal refs
DEFINITION_PATTERNS = [
    re.compile(r"^[^Đđ]*(?:là\s+)?gì\s*\??$", re.IGNORECASE | re.UNICODE),  # "X là gì?"
    re.compile(r"định\s+nghĩa", re.IGNORECASE | re.UNICODE),
    re.compile(r"giải\s+thích\s+(?:từ\s+)?(?:ngữ)?", re.IGNORECASE | re.UNICODE),
    re.compile(r"có\s+nghĩa\s+là", re.IGNORECASE | re.UNICODE),
    re.compile(r"được\s+hiểu\s+(?:là|như)", re.IGNORECASE | re.UNICODE),
]

# Question patterns for semantic queries
QUESTION_PATTERNS = [
    re.compile(r"^(?:hỏi|cho\s+hỏi|xin\s+hỏi)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?:như\s+thế\s+nào|ra\s+sao|thế\s+nào)\s*\??$", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?:có\s+)?(?:quy\s+định|nói|đề\s+cập)(?:\s+gì)?(?:\s+về)?", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?:khi\s+nào|bao\s+giờ|ở\s+đâu)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?:ai|những\s+ai|đối\s+tượng\s+nào)", re.IGNORECASE | re.UNICODE),
]

# Comparison patterns
COMPARISON_PATTERNS = [
    re.compile(r"(?:so\s+sánh|khác\s+(?:nhau|gì)|giống\s+nhau)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?:và|với)\s+[Đđ]iều\s+\d+", re.UNICODE),
]


class LegalQueryParser:
    """
    Parser for Vietnamese legal queries.
    
    Extracts legal references (law_id, article, clause, point) from queries
    and classifies the query intent.
    
    Usage:
        parser = LegalQueryParser()
        result = parser.parse("Khoản 2 Điều 11 Luật 20/2023/QH15 quy định gì?")
        
        print(result.law_id)      # "20/2023/QH15"
        print(result.article_id)  # "11"
        print(result.clause_no)   # "2"
        print(result.intent)      # QueryIntent.LOOKUP_EXACT
    """
    
    def __init__(
        self,
        law_id_patterns: Optional[List[re.Pattern]] = None,
        article_patterns: Optional[List[re.Pattern]] = None,
        clause_patterns: Optional[List[re.Pattern]] = None,
        point_patterns: Optional[List[re.Pattern]] = None,
    ):
        """
        Initialize parser with optional custom patterns.
        
        Args:
            law_id_patterns: Custom law ID regex patterns
            article_patterns: Custom article regex patterns
            clause_patterns: Custom clause regex patterns
            point_patterns: Custom point regex patterns
        """
        self.law_id_patterns = law_id_patterns or LAW_ID_PATTERNS
        self.article_patterns = article_patterns or ARTICLE_PATTERNS
        self.clause_patterns = clause_patterns or CLAUSE_PATTERNS
        self.point_patterns = point_patterns or POINT_PATTERNS
    
    def parse(self, query: str) -> LegalQuery:
        """
        Parse a legal query to extract references and classify intent.
        
        Args:
            query: Raw user query string
            
        Returns:
            LegalQuery with extracted information
        """
        if not query or not query.strip():
            return LegalQuery(
                raw=query,
                intent=QueryIntent.SEMANTIC_QUESTION,
                keywords=[],
                normalized_query=query,
            )
        
        query = query.strip()
        
        # Extract legal references
        law_id = self._extract_law_id(query)
        article_id = self._extract_article_id(query)
        clause_no = self._extract_clause_no(query)
        point_no = self._extract_point_no(query)
        
        # Classify intent
        intent = self._classify_intent(query, law_id, article_id, clause_no, point_no)
        
        # Extract keywords (remove legal refs from query)
        keywords = self._extract_keywords(query, law_id, article_id, clause_no, point_no)
        
        # Build normalized query
        normalized_query = self._normalize_query(query)
        
        # Calculate confidence
        confidence = self._calculate_confidence(law_id, article_id, clause_no, point_no, intent)
        
        return LegalQuery(
            raw=query,
            law_id=law_id,
            article_id=article_id,
            clause_no=clause_no,
            point_no=point_no,
            intent=intent,
            keywords=keywords,
            normalized_query=normalized_query,
            confidence=confidence,
        )
    
    def _extract_law_id(self, query: str) -> Optional[str]:
        """Extract law ID from query."""
        for pattern in self.law_id_patterns:
            match = pattern.search(query)
            if match:
                groups = match.groups()
                if len(groups) >= 2 and groups[0] and groups[1]:
                    # Standard format: number/year/issuer
                    number, year = groups[0], groups[1]
                    issuer = groups[2] if len(groups) > 2 and groups[2] else ""
                    if issuer:
                        return f"{number}/{year}/{issuer}"
                    else:
                        return f"{number}/{year}"
                elif len(groups) == 1 and groups[0]:
                    # Named law
                    return groups[0].strip()
        return None
    
    def _extract_article_id(self, query: str) -> Optional[str]:
        """Extract article ID from query."""
        for pattern in self.article_patterns:
            match = pattern.search(query)
            if match:
                return match.group(1)
        return None
    
    def _extract_clause_no(self, query: str) -> Optional[str]:
        """Extract clause number from query."""
        for pattern in self.clause_patterns:
            match = pattern.search(query)
            if match:
                return match.group(1)
        return None
    
    def _extract_point_no(self, query: str) -> Optional[str]:
        """Extract point letter from query."""
        for pattern in self.point_patterns:
            match = pattern.search(query)
            if match:
                return match.group(1).lower()
        return None
    
    def _classify_intent(
        self,
        query: str,
        law_id: Optional[str],
        article_id: Optional[str],
        clause_no: Optional[str],
        point_no: Optional[str],
    ) -> QueryIntent:
        """Classify query intent based on patterns and extracted refs."""
        
        # Check for comparison queries first (rare but specific)
        for pattern in COMPARISON_PATTERNS:
            if pattern.search(query):
                return QueryIntent.COMPARISON
        
        # PRIORITY: If specific point or clause is referenced, it's an exact lookup
        # This takes precedence over definition patterns
        if point_no or (clause_no and article_id):
            return QueryIntent.LOOKUP_EXACT
        
        # PRIORITY: If only article is referenced, it's an article lookup
        # This takes precedence over definition patterns
        if article_id and not clause_no and not point_no:
            return QueryIntent.LOOKUP_ARTICLE
        
        # Check for definition queries ONLY if no legal refs
        if not any([law_id, article_id, clause_no, point_no]):
            for pattern in DEFINITION_PATTERNS:
                if pattern.search(query):
                    return QueryIntent.DEFINITION
        
        # Check for question patterns
        for pattern in QUESTION_PATTERNS:
            if pattern.search(query):
                return QueryIntent.SEMANTIC_QUESTION
        
        # Default to semantic if there are no specific refs
        if not any([law_id, article_id, clause_no, point_no]):
            return QueryIntent.SEMANTIC_QUESTION
        
        # Has some legal refs but no specific provision
        return QueryIntent.LOOKUP_ARTICLE
    
    def _extract_keywords(
        self,
        query: str,
        law_id: Optional[str],
        article_id: Optional[str],
        clause_no: Optional[str],
        point_no: Optional[str],
    ) -> List[str]:
        """Extract remaining keywords after removing legal references."""
        # Remove legal references from query
        cleaned = query
        
        # Remove law patterns
        for pattern in self.law_id_patterns:
            cleaned = pattern.sub("", cleaned)
        
        # Remove article patterns
        for pattern in self.article_patterns:
            cleaned = pattern.sub("", cleaned)
        
        # Remove clause patterns
        for pattern in self.clause_patterns:
            cleaned = pattern.sub("", cleaned)
        
        # Remove point patterns
        for pattern in self.point_patterns:
            cleaned = pattern.sub("", cleaned)
        
        # Remove common filler words
        filler_words = {
            "luật", "theo", "trong", "của", "và", "hoặc", "về",
            "quy", "định", "nói", "gì", "như", "thế", "nào",
            "hỏi", "cho", "xin", "được", "có", "là",
        }
        
        # Tokenize and filter
        words = re.split(r'\s+', cleaned.lower().strip())
        keywords = [
            w for w in words
            if w and len(w) > 1 and w not in filler_words and not w.isdigit()
        ]
        
        return keywords
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for embedding (standardize legal references)."""
        normalized = query
        
        # Normalize "Điều X" to standard form
        normalized = re.sub(
            r"[Đđ]iều\s+(?:số\s+)?(\d+)",
            r"Điều \1",
            normalized
        )
        
        # Normalize "Khoản X" to standard form
        normalized = re.sub(
            r"[Kk]hoản\s+(\d+)",
            r"Khoản \1",
            normalized
        )
        
        # Normalize "Điểm X" to standard form
        normalized = re.sub(
            r"[Đđ]iểm\s+([a-zđ])",
            r"Điểm \1",
            normalized,
            flags=re.IGNORECASE
        )
        
        # Clean up extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_confidence(
        self,
        law_id: Optional[str],
        article_id: Optional[str],
        clause_no: Optional[str],
        point_no: Optional[str],
        intent: QueryIntent,
    ) -> float:
        """Calculate parser confidence score."""
        confidence = 0.5  # Base confidence
        
        # More specific references = higher confidence
        if law_id:
            confidence += 0.15
        if article_id:
            confidence += 0.15
        if clause_no:
            confidence += 0.1
        if point_no:
            confidence += 0.1
        
        # Exact lookups are high confidence
        if intent == QueryIntent.LOOKUP_EXACT:
            confidence = min(confidence + 0.1, 1.0)
        
        return min(confidence, 1.0)
    
    def parse_citation_string(self, citation: str) -> LegalQuery:
        """
        Parse a citation string (e.g., "Điểm a Khoản 2 Điều 11 Luật 20/2023/QH15").
        
        This is useful for parsing citations from documents.
        
        Args:
            citation: Citation string
            
        Returns:
            LegalQuery with extracted references
        """
        return self.parse(citation)
    
    def validate_legal_reference(
        self,
        law_id: Optional[str] = None,
        article_id: Optional[str] = None,
        clause_no: Optional[str] = None,
        point_no: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate a set of legal references for consistency.
        
        Rules:
        - Point requires clause
        - Clause requires article
        
        Args:
            law_id: Law identifier
            article_id: Article ID
            clause_no: Clause number
            point_no: Point letter
            
        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings = []
        
        if point_no and not clause_no:
            warnings.append("Điểm được chỉ định nhưng thiếu Khoản")
        
        if clause_no and not article_id:
            warnings.append("Khoản được chỉ định nhưng thiếu Điều")
        
        return len(warnings) == 0, warnings


# =============================================================================
# Convenience Functions
# =============================================================================

def parse_legal_query(query: str) -> LegalQuery:
    """
    Convenience function to parse a legal query.
    
    Args:
        query: Raw user query
        
    Returns:
        Parsed LegalQuery
    """
    parser = LegalQueryParser()
    return parser.parse(query)


def extract_legal_refs(query: str) -> Dict[str, Optional[str]]:
    """
    Extract legal references from query as dictionary.
    
    Args:
        query: Raw user query
        
    Returns:
        Dictionary with law_id, article_id, clause_no, point_no
    """
    parsed = parse_legal_query(query)
    return {
        "law_id": parsed.law_id,
        "article_id": parsed.article_id,
        "clause_no": parsed.clause_no,
        "point_no": parsed.point_no,
    }
