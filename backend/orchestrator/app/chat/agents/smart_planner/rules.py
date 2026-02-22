"""
Rule-based heuristics for Smart Planner Agent.

Contains all non-LLM logic: pattern matching, keyword extraction,
intent detection, complexity estimation, query rewriting, filter extraction.
"""

import re
from typing import List, Optional, Dict

from .models import SmartPlanResult, ExtractedFilters


# UIT-specific abbreviation mappings
UIT_ABBREVIATIONS: Dict[str, str] = {
    "hp": "học phần",
    "đkhp": "đăng ký học phần",
    "khmt": "khoa học máy tính",
    "cntt": "công nghệ thông tin",
    "httt": "hệ thống thông tin",
    "mmt": "mạng máy tính và truyền thông",
    "mmtt": "mạng máy tính và truyền thông",
    "sv": "sinh viên",
    "gv": "giảng viên",
    "đtbc": "điểm trung bình chung",
    "ctđt": "chương trình đào tạo",
    "uit": "đại học công nghệ thông tin",
    "đhqg": "đại học quốc gia",
    "hcm": "hồ chí minh",
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
        "chuyển ngành", "chuyển trường", "chuyển chương trình",
        "bảo lưu", "thôi học", "tốt nghiệp", "xét tốt nghiệp",
        "khen thưởng", "kỷ luật", "học bổng",
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
        r'nếu.*(rớt|trượt|không qua|fail).*thì',
        r'nếu.*(không học|bỏ qua|skip).*thì',
        r'(rớt|trượt).*ảnh hưởng',
        r'(rớt|trượt).*bị trễ',
        r'chuỗi.*(môn|học phần)',
        r'từ.*(cơ sở|nền tảng).*đến.*(chuyên ngành|nâng cao)',
        r'đường đi.*học', r'lộ trình.*học',
        r'ảnh hưởng.*như thế nào.*tốt nghiệp',
        r'tác động.*đến.*năm (cuối|\d)',
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
        r'so sánh.*(chương trình|ngành|khoa)',
        r'khác biệt.*(giữa|của).*(chương trình|ngành|khoa)',
        r'(cntt|khmt|httt|mmt).*(vs|so với|và).*(cntt|khmt|httt|mmt)',
        r'tóm tắt.*(quy định|chương trình|môn học)',
        r'tổng quan.*(về|của)',
        r'liệt kê tất cả.*(môn|chương trình)',
        r'có bao nhiêu (môn|quy định|điều)',
        r'phân loại.*(môn|quy định)',
        r'nhóm.*(môn học|quy định)',
    ]
    for pattern in global_patterns:
        if re.search(pattern, query_lower):
            return "global"

    # LOCAL patterns (simple lookup)
    local_patterns = [
        r'(tiên quyết|học trước|cần học)',
        r'môn.*(trước|sau)',
        r'(thuộc|của) khoa',
        r'môn.*(bắt buộc|tự chọn)',
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
    for abbr, full in UIT_ABBREVIATIONS.items():
        if abbr in expanded:
            expanded = expanded.replace(abbr, full)
    if expanded != query_lower:
        rewritten.append(expanded)

    if "uit" not in query_lower and "đại học công nghệ" not in query_lower:
        rewritten.append(f"{query} tại UIT")

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
    Extract search filters (faculties, years, subjects) from query context.
    """
    query_lower = query.lower()
    filters = ExtractedFilters()

    # Faculties detection
    faculty_patterns = {
        "CNTT": ["công nghệ thông tin", "cntt", "khoa cntt"],
        "KHMT": ["khoa học máy tính", "khmt", "computer science"],
        "HTTT": ["hệ thống thông tin", "httt", "information systems"],
        "MMT": ["mạng máy tính", "mmt", "mmtt", "truyền thông", "network"],
        "KTMT": ["kỹ thuật máy tính", "ktmt", "computer engineering"],
        "KHTN": ["khoa học tự nhiên", "khtn"],
        "CTDA": ["công trình đa âm", "ctda"],
    }
    for faculty, patterns in faculty_patterns.items():
        if any(p in query_lower for p in patterns):
            filters.faculties.append(faculty)

    # Years detection
    year_patterns = [
        r'năm\s*(\d{4})', r'khóa\s*(\d{4})', r'niên khóa\s*(\d{4})',
        r'(\d{4})\s*[-–]\s*\d{4}', r'\b(20\d{2})\b',
    ]
    for pattern in year_patterns:
        for match in re.findall(pattern, query_lower):
            try:
                year = int(match)
                if 2000 <= year <= 2100 and year not in filters.years:
                    filters.years.append(year)
            except ValueError:
                continue

    # Subjects detection (codes like SE101, CS201)
    subject_pattern = r'\b([A-Z]{2,4}\d{3})\b'
    for match in re.findall(subject_pattern, query.upper()):
        if match not in filters.subjects:
            filters.subjects.append(match)

    # Common subject name → code mapping
    subject_name_patterns = {
        "IT001": ["nhập môn lập trình", "intro to programming"],
        "IT002": ["lập trình hướng đối tượng", "oop"],
        "IT003": ["cấu trúc dữ liệu", "data structures"],
        "SE100": ["nhập môn công nghệ phần mềm"],
        "SE101": ["công nghệ phần mềm"],
    }
    for code, patterns in subject_name_patterns.items():
        if any(p in query_lower for p in patterns) and code not in filters.subjects:
            filters.subjects.append(code)

    return filters
