"""Test the document filter in Answer Agent."""
import sys
sys.path.insert(0, r"c:\Users\admin\Downloads\Khiem\Chatbot-UIT\services\orchestrator")

# Test the filter logic standalone
import re

def filter_amended_documents(context_documents):
    """Filter documents to prioritize amended content."""
    article_map = {}
    other_docs = []
    
    for doc in context_documents:
        title = doc.get("title", "") or ""
        content = doc.get("content", "") or doc.get("text", "") or ""
        is_amended = doc.get("is_amended", False)
        
        article_match = re.search(r'Điều\s*(\d+)', title, re.IGNORECASE)
        
        if article_match:
            article_num = article_match.group(1)
            
            # Check if content has OLD markers
            old_markers = [
                "ĐTBC ≥ 7" in content or "ĐTBC >= 7" in content,
                "điểm trung bình chung ≥ 7" in content.lower(),
                "học vượt chỉ dành cho sinh viên có ĐTBC" in content,
            ]
            has_old_markers = any(old_markers)
            
            # Check if this is amendment content
            new_markers = [
                is_amended,
                "Mục" in title and "Điều" in title,
                doc.get("source", "") == "knowledge_graph",
            ]
            is_new_content = any(new_markers)
            
            if article_num in article_map:
                existing_doc, existing_is_amended = article_map[article_num]
                if is_new_content and not existing_is_amended:
                    article_map[article_num] = (doc, is_new_content)
                elif has_old_markers:
                    pass
                elif not is_new_content and existing_is_amended:
                    pass
            else:
                if not has_old_markers or is_new_content:
                    article_map[article_num] = (doc, is_new_content)
        else:
            other_docs.append(doc)
    
    filtered = [doc for doc, _ in article_map.values()] + other_docs
    return filtered

# Simulate documents from both sources
test_docs = [
    {
        "title": "Điều 14. Đăng ký học tập",
        "content": "Sinh viên có ĐTBC ≥ 7.0 mới được đăng ký học vượt...",  # OLD content
        "source": "opensearch",
        "is_amended": False
    },
    {
        "title": "Mục b khoản 1 Điều 14",
        "content": "Trong học kỳ hè - Tổng số tín chỉ không vượt quá 12 tín chỉ. Sinh viên được đăng ký học mới, học lại...",  # NEW content
        "source": "opensearch",
        "is_amended": False
    },
    {
        "title": "Điều 14. Đăng ký học tập",
        "content": "Trong học kỳ hè - Tổng số tín chỉ không vượt quá 12 tín chỉ...",  # NEW from Neo4j
        "source": "knowledge_graph",
        "is_amended": True
    },
    {
        "title": "Khoản 2 Điều 5",
        "content": "Một năm học có 2 học kỳ chính...",
        "source": "opensearch",
        "is_amended": False
    }
]

print("="*70)
print("INPUT: 4 documents (2 old, 2 new)")
print("="*70)
for i, doc in enumerate(test_docs):
    print(f"{i+1}. {doc['title']} (source: {doc['source']}, amended: {doc['is_amended']})")
    print(f"   Content preview: {doc['content'][:60]}...")

print("\n" + "="*70)
print("OUTPUT after filter:")
print("="*70)
filtered = filter_amended_documents(test_docs)

for i, doc in enumerate(filtered):
    print(f"{i+1}. {doc['title']} (source: {doc.get('source')}, amended: {doc.get('is_amended')})")
    has_dtbc = "ĐTBC" in doc.get('content', '')
    status = "❌ OLD" if has_dtbc else "✓ NEW"
    print(f"   {status}: {doc.get('content', '')[:60]}...")

print("\n" + "="*70)
if any("ĐTBC" in doc.get('content', '') for doc in filtered):
    print("⚠️ FAILED: Old content still present!")
else:
    print("✅ SUCCESS: Only new content remains!")
