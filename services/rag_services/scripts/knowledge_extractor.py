# services/rag_services/scripts/knowledge_extractor.py
import re
import fitz  # PyMuPDF
import json
import nltk
nltk.download("punkt", quiet=True)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Trích xuất toàn bộ nội dung từ file PDF."""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return re.sub(r'\s+', ' ', text).strip()

def sentence_split(text: str):
    """Tách câu đơn giản bằng nltk."""
    return nltk.sent_tokenize(text, language='english')

def extract_knowledge_triples(sentences):
    """Dò tìm các mối quan hệ cơ bản trong văn bản."""
    triples = []

    # Các mẫu quan hệ phổ biến trong quy chế đào tạo
    patterns = [
        (r"(Sinh viên|Người học) (được phép|phải|có trách nhiệm|có quyền|không được) ([^\.]*)", None),
        (r"(Quy chế|Quy định) (liên quan đến|áp dụng cho|được ban hành bởi|được thực hiện bởi) ([^\.]*)", None),
        (r"(Hiệu trưởng) (ban hành|ký ban hành|chịu trách nhiệm|là người đứng đầu của) ([^\.]*)", None),
        (r"(Học phần|Môn học) (bao gồm|có|được tính là|thuộc) ([^\.]*)", None),
        (r"(Điểm|Kết quả học tập) (được tính|được quy đổi|phản ánh) ([^\.]*)", None)
    ]

    for sent in sentences:
        for pattern, relation in patterns:
            match = re.search(pattern, sent, re.IGNORECASE)
            if match:
                subj = match.group(1)
                rel = match.group(2)
                obj = match.group(3)
                triples.append((subj.strip(), rel.strip(), obj.strip()))
    return triples

def main():
    pdf_path = "services/rag_services/data/quy_dinh/790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf"
    print(f"🔍 Đang đọc nội dung từ: {pdf_path}")

    text = extract_text_from_pdf(pdf_path)
    sentences = sentence_split(text)
    triples = extract_knowledge_triples(sentences)

    print(f"✅ Trích xuất được {len(triples)} bộ ba tri thức.")
    
    # Lưu ra file JSON để chatbot có thể nạp vào hệ RAG
    output_path = "services/rag_services/data/knowledge_triples.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(triples, f, ensure_ascii=False, indent=2)
    
    print(f"📁 Đã lưu kết quả vào: {output_path}")

if __name__ == "__main__":
    main()

