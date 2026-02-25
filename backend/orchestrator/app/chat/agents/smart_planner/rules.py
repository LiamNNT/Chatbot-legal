"""
Rule-based heuristics for Smart Planner Agent.

Contains all non-LLM logic: pattern matching, keyword extraction,
intent detection, complexity estimation, query rewriting, filter extraction.
"""

import re
from typing import List, Optional, Dict

from .models import SmartPlanResult, ExtractedFilters


# Legal abbreviation mappings
LEGAL_ABBREVIATIONS: Dict[str, str] = {
    "nđ": "nghị định",
    "tt": "thông tư",
    "qđ": "quyết định",
    "cp": "chính phủ",
    "blhs": "bộ luật hình sự",
    "blds": "bộ luật dân sự",
    "bllđ": "bộ luật lao động",
    "blttds": "bộ luật tố tụng dân sự",
    "bltths": "bộ luật tố tụng hình sự",
    "xphc": "xử phạt hành chính",
    "vbpl": "văn bản pháp luật",
    "qh": "quốc hội",
    "ttcp": "thủ tướng chính phủ",
    "ubnd": "ủy ban nhân dân",
    "hđnd": "hội đồng nhân dân",
}


def check_simple_query(query: str) -> Optional[SmartPlanResult]:
    """
    Check if query is simple enough to handle without LLM.
    Returns SmartPlanResult for simple queries, None otherwise.
    """
    query_lower = query.lower().strip()

    # Identity questions
    identity_patterns = [
        "bạn là ai", "bạn là gì", "mày là ai", "who are you",
        "bạn tên gì", "tên bạn là gì", "bạn là chatbot gì",
    ]
    for pattern in identity_patterns:
        if pattern in query_lower:
            return SmartPlanResult(
                query=query, intent="social_greeting", complexity="simple",
                complexity_score=0.0, requires_rag=False, strategy="direct_response",
                rewritten_queries=[], search_terms=[], top_k=0,
                hybrid_search=False, reranking=False,
                reasoning="Identity question - direct response about chatbot",
                confidence=1.0, metadata={"rule_based": True, "pattern_matched": pattern},
            )

    # Social/greeting patterns
    social_patterns = [
        "xin chào", "hello", "hi", "chào", "cảm ơn", "thanks", "thank you",
        "tạm biệt", "bye", "ok", "được", "vâng", "dạ", "ừ", "oke",
    ]
    for pattern in social_patterns:
        if query_lower == pattern or query_lower.startswith(pattern + " "):
            return SmartPlanResult(
                query=query, intent="social_greeting", complexity="simple",
                complexity_score=0.0, requires_rag=False, strategy="direct_response",
                rewritten_queries=[], search_terms=[], top_k=0,
                hybrid_search=False, reranking=False,
                reasoning="Detected social/greeting query, no RAG needed",
                confidence=1.0, metadata={"rule_based": True, "pattern_matched": pattern},
            )

    return None


def detect_intent(query: str) -> str:
    """Detect query intent using rule-based approach."""
    query_lower = query.lower()

    if any(p in query_lower for p in ["xin chào", "hello", "cảm ơn", "tạm biệt"]):
        return "social_greeting"
    if any(p in query_lower for p in ["so sánh", "khác biệt", "giống nhau", "vs"]):
        return "comparative"
    if any(p in query_lower for p in ["cách", "làm sao", "thế nào", "quy trình", "hướng dẫn"]):
        return "procedural"
    return "informational"


def estimate_complexity_score(query: str) -> float:
    """Estimate complexity score (0-10) using heuristics."""
    score = 5.0
    query_lower = query.lower()

    simple_patterns = ["xin chào", "hello", "cảm ơn", "tạm biệt", "ok"]
    if any(p in query_lower for p in simple_patterns):
        return 1.0

    if len(query) < 20:
        score -= 2.0
    elif len(query) < 40:
        score -= 1.0

    complex_patterns = [
        "so sánh", "phân tích", "đánh giá", "quy trình chi tiết",
        "hướng dẫn", "các bước", "làm thế nào", "khác biệt",
    ]
    if any(p in query_lower for p in complex_patterns):
        score += 2.5

    if query.count("?") > 1:
        score += 1.0
    if len(query) > 100:
        score += 1.5
    elif len(query) > 60:
        score += 0.5

    return max(0, min(10, score))


def score_to_complexity(score: float, simple_max: float = 3.5, complex_min: float = 6.5) -> str:
    """Convert complexity score to label."""
    if score <= simple_max:
        return "simple"
    elif score >= complex_min:
        return "complex"
    return "medium"


def needs_knowledge_graph(query: str) -> bool:
    """
    Determine if the query would benefit from Knowledge Graph search.
    
    KG is useful for: article/regulation references, relationship queries,
    conditions/requirements questions, structured data lookups.
    """
    query_lower = query.lower()

    relationship_patterns = [
        "mối quan hệ", "quan hệ", "liên quan", "liên kết",
        "kết nối", "ảnh hưởng", "tác động", "phụ thuộc",
        "dẫn đến", "gây ra", "bắt nguồn từ",
    ]
    regulation_patterns = ["khoản", "mục", "chương", "quy chế", "nghị định", "thông tư"]
    regulation_questions = [
        "điều kiện", "yêu cầu", "quy định", "thủ tục", "hồ sơ",
        "chế tài", "hình phạt", "mức phạt", "xử phạt",
        "hành vi", "vi phạm", "nghĩa vụ", "quyền",
        "trách nhiệm", "thẩm quyền", "hiệu lực",
        "cấm", "bị cấm", "không được phép",
    ]

    has_relationship = any(p in query_lower for p in relationship_patterns)
    has_regulation = any(p in query_lower for p in regulation_patterns)
    has_regulation_question = any(p in query_lower for p in regulation_questions)

    article_pattern = r'điều\s+(\d+)'
    article_matches = re.findall(article_pattern, query_lower)
    unique_articles = set(article_matches)
    has_single_article = len(unique_articles) >= 1
    has_multiple_articles = len(unique_articles) >= 2

    comparative_regulation = (
        (has_regulation or len(unique_articles) >= 1)
        and any(p in query_lower for p in ["so sánh", "khác", "giống", "với"])
    )

    return (
        has_relationship
        or has_single_article
        or has_multiple_articles
        or comparative_regulation
        or has_regulation
        or has_regulation_question
    )


def determine_graph_query_type(query: str) -> str:
    """
    Determine the type of graph query needed.
    
    Returns: "local", "global", or "multi_hop"
    """
    query_lower = query.lower()

    # MULTI_HOP patterns
    multi_hop_patterns = [
        r'nếu.*vi phạm.*thì.*bị',
        r'nếu.*không.*tuân thủ.*thì',
        r'hành vi.*bị.*xử phạt.*như thế nào',
        r'mối quan hệ.*giữa.*luật.*và.*nghị định',
        r'nghị định.*hướng dẫn.*luật',
        r'thông tư.*hướng dẫn.*nghị định',
        r'từ.*vi phạm.*đến.*chế tài',
        r'ảnh hưởng.*như thế nào',
        r'tác động.*đến',
        r'dẫn chiếu.*đến',
        r'liên quan.*đến.*điều',
    ]
    for pattern in multi_hop_patterns:
        if re.search(pattern, query_lower):
            return "multi_hop"

    # LOCAL patterns (relationship scanning)
    relationship_scan_patterns = [
        r'liệt kê.*(có|với).*(quan hệ|mối quan hệ).*(yeu_cau|quy_dinh|điều kiện)',
        r'(các điều|điều khoản).*(có|với).*(quan hệ|relationship)',
        r'scan.*relationship',
        r'tìm.*(các cặp|cặp).*(có|với).*quan hệ',
    ]
    for pattern in relationship_scan_patterns:
        if re.search(pattern, query_lower):
            return "local"

    # GLOBAL patterns
    global_patterns = [
        r'so sánh.*(luật|nghị định|thông tư|quy định)',
        r'khác biệt.*(giữa|của).*(luật|nghị định|phiên bản)',
        r'tóm tắt.*(quy định|luật|nghị định|thông tư)',
        r'tổng quan.*(về|của)',
        r'liệt kê tất cả.*(điều|khoản|quy định|chế tài)',
        r'có bao nhiêu (điều|khoản|quy định|hành vi)',
        r'phân loại.*(vi phạm|chế tài|hành vi)',
        r'nhóm.*(vi phạm|quy định)',
        r'các loại.*(hình phạt|chế tài|vi phạm)',
    ]
    for pattern in global_patterns:
        if re.search(pattern, query_lower):
            return "global"

    # LOCAL patterns (simple lookup)
    local_patterns = [
        r'(nội dung|quy định).*(điều|khoản)',
        r'điều\s*\d+',
        r'khoản\s*\d+',
        r'(thuộc|của|trong).*(luật|nghị định|thông tư)',
        r'(mức phạt|hình phạt|chế tài).*cụ thể',
        r'^(cho biết|thông tin về)',
    ]
    for pattern in local_patterns:
        if re.search(pattern, query_lower):
            return "local"

    return "local"


def apply_rule_based_rewriting(query: str, max_queries: int = 3) -> List[str]:
    """Apply rule-based query rewriting with abbreviation expansion."""
    query_lower = query.lower()
    rewritten = []

    expanded = query_lower
    for abbr, full in LEGAL_ABBREVIATIONS.items():
        if abbr in expanded:
            expanded = expanded.replace(abbr, full)
    if expanded != query_lower:
        rewritten.append(expanded)

    if query not in rewritten:
        rewritten.insert(0, query)

    return rewritten[:max_queries]


def extract_keywords(query: str, max_keywords: int = 10) -> List[str]:
    """Extract important keywords from query."""
    stop_words = {
        "là", "của", "và", "có", "trong", "với", "để", "về", "tại", "từ",
        "này", "đó", "những", "các", "một", "như", "được", "sẽ", "đã",
        "đang", "thì", "nếu", "khi", "mà", "hay", "hoặc", "gì", "nào",
    }
    words = query.lower().replace(",", " ").replace(".", " ").split()
    keywords = [w.strip("?!.,;:") for w in words if len(w.strip("?!.,;:")) > 2 and w.strip("?!.,;:") not in stop_words]
    return keywords[:max_keywords]


def extract_filters_from_query(query: str) -> ExtractedFilters:
    """
    Extract search filters (legal domains, years, legal references) from query context.
    """
    query_lower = query.lower()
    filters = ExtractedFilters()

    # Legal domain detection
    domain_patterns = {
        "hình_sự": ["hình sự", "tội phạm", "hình phạt", "blhs"],
        "dân_sự": ["dân sự", "hợp đồng", "bồi thường", "blds"],
        "hành_chính": ["hành chính", "xử phạt", "vi phạm hành chính", "xphc"],
        "lao_động": ["lao động", "người lao động", "người sử dụng lao động", "bllđ"],
        "thương_mại": ["thương mại", "doanh nghiệp", "kinh doanh"],
        "giao_thông": ["giao thông", "đường bộ", "phương tiện"],
        "đất_đai": ["đất đai", "quyền sử dụng đất", "bất động sản"],
        "thuế": ["thuế", "thuế thu nhập", "thuế giá trị gia tăng"],
    }
    for domain, patterns in domain_patterns.items():
        if any(p in query_lower for p in patterns):
            filters.legal_domains.append(domain)

    # Document type detection
    doc_type_patterns = {
        "luật": ["luật", "bộ luật"],
        "nghị_định": ["nghị định", "nđ"],
        "thông_tư": ["thông tư", "tt"],
        "quyết_định": ["quyết định", "qđ"],
        "nghị_quyết": ["nghị quyết"],
    }
    for doc_type, patterns in doc_type_patterns.items():
        if any(p in query_lower for p in patterns):
            filters.doc_types.append(doc_type)

    # Years detection
    year_patterns = [
        r'năm\s*(\d{4})', r'số\s*(\d+)/(\d{4})',
        r'(\d{4})\s*[-–]\s*\d{4}', r'\b(20\d{2})\b',
    ]
    for pattern in year_patterns:
        for match in re.findall(pattern, query_lower):
            try:
                year = int(match) if isinstance(match, str) else int(match[-1])
                if 1945 <= year <= 2100 and year not in filters.years:
                    filters.years.append(year)
            except (ValueError, IndexError):
                continue

    # Legal reference detection (Điều X, Khoản Y, Nghị định số X)
    article_refs = re.findall(r'điều\s*\d+', query_lower)
    clause_refs = re.findall(r'khoản\s*\d+', query_lower)
    decree_refs = re.findall(r'nghị \u0111ịnh\s*(?:số\s*)?\d+', query_lower)
    for ref in article_refs + clause_refs + decree_refs:
        ref_clean = ref.strip()
        if ref_clean and ref_clean not in filters.legal_references:
            filters.legal_references.append(ref_clean)

    return filters
