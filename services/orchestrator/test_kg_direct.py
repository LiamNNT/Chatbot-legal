#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct test of Knowledge Graph detection logic
"""
import sys
import re

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def needs_knowledge_graph(query: str) -> bool:
    """Check if query needs Knowledge Graph based on patterns."""
    query_lower = query.lower()
    
    # Relationship indicators
    relationship_patterns = [
        "mối quan hệ", "quan hệ", "liên quan", "liên kết",
        "kết nối", "ảnh hưởng", "tác động", "phụ thuộc",
        "dẫn đến", "gây ra", "bắt nguồn từ"
    ]
    
    # Article/regulation reference patterns  
    regulation_patterns = [
        "khoản", "mục", "chương", "quy chế", "nghị định", "thông tư"
    ]
    
    # Regulation-related question patterns
    regulation_questions = [
        "điều kiện", "yêu cầu", "quy định", "thủ tục", "hồ sơ",
        "chuyển ngành", "chuyển trường", "chuyển chương trình",
        "bảo lưu", "thôi học", "tốt nghiệp", "xét tốt nghiệp",
        "khen thưởng", "kỷ luật", "học bổng"
    ]
    
    # Check for relationship keywords
    has_relationship = any(p in query_lower for p in relationship_patterns)
    
    # Check for regulation/article references
    has_regulation = any(p in query_lower for p in regulation_patterns)
    
    # Check for regulation-related questions
    has_regulation_question = any(p in query_lower for p in regulation_questions)
    
    # Article pattern
    article_pattern = r'điều\s+(\d+)'
    article_matches = re.findall(article_pattern, query_lower)
    unique_articles = set(article_matches)
    has_single_article = len(unique_articles) >= 1
    has_multiple_articles = len(unique_articles) >= 2
    
    # Comparative patterns
    comparative_regulation = (
        (has_regulation or len(unique_articles) >= 1) and 
        any(p in query_lower for p in ["so sánh", "khác", "giống", "với"])
    )
    
    # Print debug info
    print(f"\n🔍 PATTERN ANALYSIS:")
    print(f"  has_relationship: {has_relationship}")
    print(f"  has_regulation: {has_regulation}")
    print(f"  has_regulation_question: {has_regulation_question}")
    print(f"  has_single_article: {has_single_article} (articles: {unique_articles})")
    print(f"  has_multiple_articles: {has_multiple_articles}")
    print(f"  comparative_regulation: {comparative_regulation}")
    
    result = (
        has_relationship or
        has_single_article or
        has_multiple_articles or
        comparative_regulation or
        has_regulation or
        has_regulation_question
    )
    
    return result


if __name__ == "__main__":
    test_queries = [
        "Liệt kê tất cả các điều có mối quan hệ YEU_CAU hoặc QUY_DINH_DIEU_KIEN với nhau trong quy chế",
        "So sánh chi tiết điều kiện chuyển ngành và chuyển trường",
        "Điều 19 quy định gì?",
        "Các môn học của ngành KHMT?",
        "Xin chào"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"📤 Query: {query}")
        result = needs_knowledge_graph(query)
        print(f"\n{'✅' if result else '❌'} USE_KG: {result}")
        print(f"{'='*80}")
