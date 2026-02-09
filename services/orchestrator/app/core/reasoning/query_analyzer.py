import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueryComponents:
    original_query: str
    intent: str
    concepts: List[str] = field(default_factory=list)
    legal_refs: List[Dict[str, str]] = field(default_factory=list)
    entity_type: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    query_type: str = "general"  # yes_no, what, how, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for rule matching."""
        return {
            "original_query": self.original_query,
            "intent": self.intent,
            "concepts": self.concepts,
            "legal_refs": self.legal_refs,
            "entity_type": self.entity_type,
            "keywords": self.keywords,
            "query_type": self.query_type
        }


class QueryAnalyzer:
    # Intent detection keywords
    INTENT_PATTERNS = {
        "permission_check": [
            "có được", "có được phép", "có thể", "có quyền",
            "được phép", "có được không", "có vi phạm"
        ],
        "prohibition_query": [
            "nghiêm cấm", "cấm", "không được", "bị cấm",
            "vi phạm", "trái pháp luật"
        ],
        "definition": [
            "là gì", "nghĩa là gì", "định nghĩa", "hiểu như thế nào",
            "thế nào là", "khái niệm"
        ],
        "obligation_query": [
            "trách nhiệm", "nghĩa vụ", "phải", "bắt buộc",
            "yêu cầu", "phải làm gì", "cần phải"
        ],
        "rights_query": [
            "quyền", "quyền lợi", "được bảo vệ", "được hưởng",
            "quyền được", "có quyền"
        ],
        "violation_query": [
            "vi phạm", "xử phạt", "bị phạt", "hình phạt",
            "chế tài", "xử lý", "bị xử"
        ],
        "regulation_query": [
            "quy định", "điều chỉnh", "theo luật", "pháp luật",
            "văn bản", "nội dung"
        ],
        "relation_query": [
            "liên quan", "có liên quan", "quan hệ", "mối liên hệ",
            "tác động", "ảnh hưởng"
        ],
        "requirement_query": [
            "điều kiện", "yêu cầu", "tiêu chuẩn", "cần đáp ứng",
            "phải có", "cần có"
        ],
        "compliance_query": [
            "tuân thủ", "chấp hành", "thực hiện", "áp dụng",
            "theo quy định"
        ]
    }
    
    # Legal concept keywords
    CONCEPT_KEYWORDS = [
        # Cybersecurity concepts
        "an ninh mạng", "an ninh quốc gia", "trật tự an toàn xã hội",
        "không gian mạng", "bảo vệ dữ liệu", "dữ liệu cá nhân",
        "thông tin cá nhân", "bí mật kinh doanh", "tấn công mạng",
        "gián điệp mạng", "khủng bố mạng", "mạng xã hội",
        "dịch vụ mạng", "an toàn thông tin", "bảo mật thông tin",
        
        # Rights and obligations
        "quyền con người", "tự do ngôn luận", "quyền riêng tư",
        "quyền tự do", "quyền được bảo vệ", "nghĩa vụ",
        "trách nhiệm pháp lý",
        
        # Entities
        "doanh nghiệp", "tổ chức", "cá nhân", "công dân",
        "cơ quan nhà nước", "người sử dụng", "nhà cung cấp",
        
        # Actions
        "thu thập dữ liệu", "xử lý dữ liệu", "lưu trữ dữ liệu",
        "chia sẻ thông tin", "phát tán thông tin", "công bố thông tin",
        
        # Education (UIT specific)
        "học phần", "môn học", "tín chỉ", "đăng ký học",
        "điểm", "điều kiện tiên quyết", "tốt nghiệp",
        "chương trình đào tạo", "sinh viên"
    ]
    
    # Entity type patterns
    ENTITY_TYPE_PATTERNS = {
        "ORGANIZATION": [
            "doanh nghiệp", "công ty", "tổ chức", "cơ quan",
            "đơn vị", "nhà cung cấp", "doanh nghiệp nước ngoài"
        ],
        "INDIVIDUAL": [
            "cá nhân", "công dân", "người", "người sử dụng",
            "người dùng", "sinh viên"
        ],
        "GOVERNMENT": [
            "cơ quan nhà nước", "chính phủ", "bộ", "ủy ban",
            "quốc hội"
        ]
    }
    
    # Question type patterns
    QUESTION_TYPE_PATTERNS = {
        "yes_no": ["có", "không", "phải không", "đúng không"],
        "what": ["là gì", "gì", "những gì"],
        "how": ["như thế nào", "thế nào", "cách nào", "làm sao"],
        "why": ["tại sao", "vì sao", "lý do"],
        "who": ["ai", "những ai", "đối tượng nào"],
        "when": ["khi nào", "lúc nào", "thời điểm"],
        "where": ["ở đâu", "nơi nào"]
    }
    
    def __init__(self, custom_concepts: Optional[List[str]] = None):
        """
        Initialize query analyzer.
        
        Args:
            custom_concepts: Additional domain-specific concepts
        """
        self.concepts = self.CONCEPT_KEYWORDS.copy()
        if custom_concepts:
            self.concepts.extend(custom_concepts)
        
        logger.info(f"QueryAnalyzer initialized with {len(self.concepts)} concepts")
    
    def analyze(self, query: str) -> QueryComponents:
        """
        Analyze a user query to extract all components.
        
        Args:
            query: User's natural language query
            
        Returns:
            QueryComponents with all extracted information
        """
        query_lower = query.lower()
        
        # Detect intent
        intent = self._detect_intent(query_lower)
        
        # Extract legal references
        legal_refs = self._extract_legal_refs(query)
        
        # Extract concepts
        concepts = self._extract_concepts(query_lower)
        
        # Detect entity type
        entity_type = self._detect_entity_type(query_lower)
        
        # Detect question type
        query_type = self._detect_question_type(query_lower)
        
        # Extract keywords
        keywords = self._extract_keywords(query_lower, concepts)
        
        components = QueryComponents(
            original_query=query,
            intent=intent,
            concepts=concepts,
            legal_refs=legal_refs,
            entity_type=entity_type,
            keywords=keywords,
            query_type=query_type
        )
        
        logger.info(
            f"Query analyzed: intent={intent}, "
            f"concepts={len(concepts)}, "
            f"legal_refs={len(legal_refs)}, "
            f"entity_type={entity_type}"
        )
        
        return components
    
    def _detect_intent(self, query_lower: str) -> str:
        """Detect user intent from query."""
        # Check each intent pattern
        intent_scores = {}
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if p in query_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Return highest scoring intent
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        
        return "general_query"
    
    def _extract_legal_refs(self, query: str) -> List[Dict[str, str]]:
        """
        Extract legal references (Law, Article, Clause, Point).
        
        Examples:
        - "Điều 26" → {"type": "ARTICLE", "value": "26"}
        - "Khoản 3" → {"type": "CLAUSE", "value": "3"}
        - "Luật An ninh mạng" → {"type": "LAW", "value": "Luật An ninh mạng"}
        """
        refs = []
        
        # Extract law names (Vietnamese)
        law_patterns = [
            r'Luật\s+[A-ZĐa-zđàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ\s]+',
            r'Nghị định\s+\d+[^\s,\.]*',
            r'Thông tư\s+\d+[^\s,\.]*',
            r'Quy chế[^,\.]+',
        ]
        
        for pattern in law_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                refs.append({"type": "LAW", "value": match.strip()})
        
        # Extract articles (Điều)
        article_pattern = r'[Đđ]iều\s+(\d+)'
        for match in re.findall(article_pattern, query):
            refs.append({"type": "ARTICLE", "value": match})
        
        # Extract clauses (Khoản)
        clause_pattern = r'[Kk]hoản\s+(\d+)'
        for match in re.findall(clause_pattern, query):
            refs.append({"type": "CLAUSE", "value": match})
        
        # Extract points (Điểm)
        point_pattern = r'[Đđ]iểm\s+([a-zđ])'
        for match in re.findall(point_pattern, query):
            refs.append({"type": "POINT", "value": match})
        
        # Extract chapters (Chương)
        chapter_pattern = r'[Cc]hương\s+([IVXLCDM]+|\d+)'
        for match in re.findall(chapter_pattern, query):
            refs.append({"type": "CHAPTER", "value": match})
        
        return refs
    
    def _extract_concepts(self, query_lower: str) -> List[str]:
        """Extract legal concepts from query."""
        found_concepts = []
        
        for concept in self.concepts:
            if concept in query_lower:
                found_concepts.append(concept)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_concepts = []
        for c in found_concepts:
            if c not in seen:
                seen.add(c)
                unique_concepts.append(c)
        
        return unique_concepts
    
    def _detect_entity_type(self, query_lower: str) -> Optional[str]:
        """Detect if query is about a specific entity type."""
        for entity_type, patterns in self.ENTITY_TYPE_PATTERNS.items():
            if any(p in query_lower for p in patterns):
                return entity_type
        return None
    
    def _detect_question_type(self, query_lower: str) -> str:
        """Detect the type of question (what, how, yes/no, etc.)."""
        for q_type, patterns in self.QUESTION_TYPE_PATTERNS.items():
            if any(p in query_lower for p in patterns):
                return q_type
        return "general"
    
    def _extract_keywords(
        self,
        query_lower: str,
        concepts: List[str]
    ) -> List[str]:
        """
        Extract additional keywords not covered by concepts.
        
        Args:
            query_lower: Lowercase query
            concepts: Already extracted concepts
            
        Returns:
            List of additional keywords
        """
        # Vietnamese stop words to filter out
        stop_words = {
            "là", "và", "hoặc", "nhưng", "của", "trong", "ngoài",
            "với", "theo", "về", "cho", "được", "bị", "đã", "sẽ",
            "có", "không", "này", "đó", "như", "thế", "nào", "gì",
            "ai", "đâu", "khi", "nếu", "thì", "vì", "để", "mà",
            "những", "các", "một", "hai", "ba", "bốn", "năm"
        }
        
        # Simple tokenization
        words = re.findall(r'\b[\wàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+\b', query_lower)
        
        # Filter
        keywords = [
            w for w in words
            if w not in stop_words
            and len(w) > 1
            and not any(w in c for c in concepts)
        ]
        
        return list(set(keywords))[:10]  # Limit to 10 keywords
