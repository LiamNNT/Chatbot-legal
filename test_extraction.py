"""Test script to verify amendment section extraction."""
import re

# Simulated Điều 1 full_text (based on actual data)
dieu_1_text = """
Điều 1: Sửa đổi, bổ sung một số điều của quy chế đào tạo

--- Khoản 3 Điều 4 ---
Công thức học phí mới: Học phí = Số tín chỉ x Đơn giá tín chỉ...

--- Khoản 1 Điều 12 ---
Sĩ số tối thiểu của lớp học phần là 70 sinh viên...

--- Mục b khoản 1 Điều 14 ---
Trong học kỳ hè:
- Tổng số tín chỉ đăng ký không được vượt quá 12 tín chỉ.
- Sinh viên được đăng ký học mới, học lại và cải thiện điểm nếu có nhu cầu. Trường thực hiện mở các lớp đủ sĩ số theo quy định, không mở lớp sĩ số ít.

--- Khoản 1 Điều 23 ---
Điều kiện miễn học phần mới...
"""

def extract_amendment_section(amending_text: str, original_title: str) -> str:
    """Extract the specific amendment section for an article."""
    
    if not amending_text or not original_title:
        return None
        
    # Extract the article number from title (e.g., "Điều 14" -> "14")
    article_match = re.search(r'Điều\s*(\d+)', original_title, re.IGNORECASE)
    if not article_match:
        return None
        
    article_number = article_match.group(1)
    
    # Pattern to find section markers
    section_pattern = rf'---[^-]*Điều\s*{article_number}\s*---\s*(.*?)(?=---|\Z)'
    
    match = re.search(section_pattern, amending_text, re.DOTALL | re.IGNORECASE)
    
    if match:
        extracted = match.group(1).strip()
        if extracted:
            return extracted
    
    return None

# Test extraction for different articles
print("="*60)
print("TEST: Extracting amendment sections from Điều 1")
print("="*60)

test_articles = ["Điều 4", "Điều 12", "Điều 14", "Điều 23"]

for article in test_articles:
    print(f"\n--- Testing: {article} ---")
    extracted = extract_amendment_section(dieu_1_text, article)
    if extracted:
        print(f"✓ Extracted ({len(extracted)} chars):")
        print(extracted[:200] + "..." if len(extracted) > 200 else extracted)
    else:
        print("✗ No match found")

print("\n" + "="*60)
print("DONE")
