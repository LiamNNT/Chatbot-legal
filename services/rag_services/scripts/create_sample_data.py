#!/usr/bin/env python3
# scripts/create_sample_data.py
#
# Description:
# Create sample Vietnamese documents for testing the enhanced hybrid search system

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_sample_documents():
    """Create sample Vietnamese documents with metadata."""
    
    sample_docs = [
        {
            "doc_id": "quy_che_tuyen_sinh_2024.pdf",
            "chunks": [
                {
                    "chunk_id": "chunk_1",
                    "title": "Quy chế tuyển sinh đại học năm 2024",
                    "text": """Quy chế tuyển sinh đại học năm 2024 quy định các điều kiện, thủ tục và quy trình tuyển sinh vào các chương trình đào tạo đại học. Thí sinh cần đạt điểm chuẩn theo từng ngành và hoàn thành hồ sơ đăng ký theo quy định. Trường đại học công nghệ thông tin cam kết tuyển sinh minh bạch, công bằng và đúng quy định của Bộ Giáo dục và Đào tạo.""",
                    "doc_type": "regulation",
                    "faculty": "CNTT",
                    "year": 2024,
                    "subject": "Tuyển sinh",
                    "metadata": {"section": "Điều kiện tuyển sinh", "page": 1}
                },
                {
                    "chunk_id": "chunk_2", 
                    "title": "Điều kiện tốt nghiệp", 
                    "text": """Để được công nhận tốt nghiệp, sinh viên phải hoàn thành đủ số tín chỉ theo chương trình đào tạo, đạt điểm trung bình tích lũy từ 2.0 trở lên và không có môn học nào bị điểm F. Sinh viên cần hoàn thành khóa luận tốt nghiệp hoặc thi tốt nghiệp theo quy định của từng ngành học.""",
                    "doc_type": "regulation",
                    "faculty": "CNTT", 
                    "year": 2024,
                    "subject": "Tốt nghiệp",
                    "metadata": {"section": "Quy định tốt nghiệp", "page": 15}
                }
            ]
        },
        {
            "doc_id": "chuong_trinh_dao_tao_cntt.pdf",
            "chunks": [
                {
                    "chunk_id": "chunk_1",
                    "title": "Chương trình đào tạo Công nghệ thông tin", 
                    "text": """Chương trình đào tạo ngành Công nghệ thông tin nhằm trang bị cho sinh viên các kiến thức cơ bản về lập trình, cơ sở dữ liệu, mạng máy tính và phát triển phần mềm. Sinh viên sẽ học các môn học như Cấu trúc dữ liệu và giải thuật, Lập trình hướng đối tượng, Cơ sở dữ liệu, Mạng máy tính và Công nghệ phần mềm.""",
                    "doc_type": "syllabus",
                    "faculty": "CNTT",
                    "year": 2024, 
                    "subject": "CNTT",
                    "metadata": {"section": "Giới thiệu chương trình", "page": 1}
                },
                {
                    "chunk_id": "chunk_2",
                    "title": "Mục tiêu đào tạo",
                    "text": """Mục tiêu của chương trình là đào tạo kỹ sư công nghệ thông tin có năng lực nghiên cứu, phát triển và ứng dụng các công nghệ thông tin tiên tiến. Sinh viên tốt nghiệp có thể làm việc trong các lĩnh vực như phát triển phần mềm, quản trị hệ thống, phân tích dữ liệu và bảo mật thông tin.""",
                    "doc_type": "syllabus",
                    "faculty": "CNTT",
                    "year": 2024,
                    "subject": "CNTT", 
                    "metadata": {"section": "Mục tiêu đào tạo", "page": 2}
                }
            ]
        },
        {
            "doc_id": "huong_dan_sinh_vien_khtn.pdf", 
            "chunks": [
                {
                    "chunk_id": "chunk_1",
                    "title": "Hướng dẫn sinh viên Khoa học tự nhiên",
                    "text": """Khoa Khoa học tự nhiên đào tạo các ngành Toán học, Vật lý, Hóa học và Sinh học. Sinh viên cần tham gia đầy đủ các buổi học lý thuyết và thực hành. Việc đánh giá kết quả học tập dựa trên bài kiểm tra giữa kỳ, cuối kỳ và các bài tập thực hành.""",
                    "doc_type": "guide",
                    "faculty": "KHTN",
                    "year": 2024,
                    "subject": "Hướng dẫn chung",
                    "metadata": {"section": "Giới thiệu khoa", "page": 1}
                },
                {
                    "chunk_id": "chunk_2",
                    "title": "Quy định thi cử và đánh giá",
                    "text": """Sinh viên phải tham dự thi đúng lịch và mang theo thẻ sinh viên. Việc gian lận trong thi cử bị nghiêm cấm và sẽ bị xử lý kỷ luật. Điểm số được tính theo thang điểm 10, trong đó điểm 5.0 trở lên là đạt yêu cầu.""",
                    "doc_type": "regulation",
                    "faculty": "KHTN", 
                    "year": 2024,
                    "subject": "Thi cử",
                    "metadata": {"section": "Quy định thi cử", "page": 8}
                }
            ]
        },
        {
            "doc_id": "tai_lieu_ctda_2023.pdf",
            "chunks": [
                {
                    "chunk_id": "chunk_1", 
                    "title": "Chương trình Chất lượng cao Công nghệ thông tin",
                    "text": """Chương trình Chất lượng cao (CLC) Công nghệ thông tin được thiết kế theo chuẩn quốc tế với học phần được giảng dạy bằng tiếng Anh. Sinh viên sẽ được học các môn học tiên tiến như Trí tuệ nhân tạo, Học máy, Khoa học dữ liệu và Blockchain.""",
                    "doc_type": "syllabus", 
                    "faculty": "CTDA",
                    "year": 2023,
                    "subject": "CLC-CNTT",
                    "metadata": {"section": "Giới thiệu chương trình CLC", "page": 1}
                }
            ]
        }
    ]
    
    return sample_docs

def index_sample_data():
    """Index sample data to OpenSearch."""
    import requests
    import time
    
    print("📚 Creating sample Vietnamese documents for testing...")
    
    documents = create_sample_documents()
    
    # Prepare bulk indexing data
    bulk_docs = []
    
    for doc in documents:
        for chunk in doc["chunks"]:
            bulk_doc = {
                "doc_id": doc["doc_id"],
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "title": chunk.get("title", ""),
                "doc_type": chunk["doc_type"], 
                "faculty": chunk["faculty"],
                "year": chunk["year"],
                "subject": chunk["subject"],
                "language": "vi",
                "metadata": chunk.get("metadata", {})
            }
            bulk_docs.append(bulk_doc)
    
    # Index documents
    try:
        print(f"📤 Indexing {len(bulk_docs)} document chunks...")
        
        response = requests.post(
            "http://localhost:8000/v1/opensearch/bulk-index",
            json={"documents": bulk_docs},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully indexed {result['successful']} documents")
            if result['failed'] > 0:
                print(f"⚠️  {result['failed']} documents failed to index")
        else:
            print(f"❌ Bulk indexing failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error indexing sample data: {e}")
        return False
    
    # Wait for indexing to complete
    print("⏳ Waiting for indexing to complete...")
    time.sleep(2)
    
    # Verify indexing
    try:
        response = requests.get("http://localhost:8000/v1/opensearch/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"📊 Index now contains {stats['total_documents']} documents")
        
    except Exception as e:
        print(f"⚠️  Could not verify indexing: {e}")
    
    return True

def test_sample_queries():
    """Test queries against the sample data."""
    print("\n🧪 Testing sample queries...")
    
    test_queries = [
        "tuyển sinh đại học",
        "điều kiện tốt nghiệp", 
        "chương trình đào tạo",
        "quy định thi cử",
        "công nghệ thông tin"
    ]
    
    import requests
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        
        try:
            # Test Vietnamese BM25
            response = requests.post(
                "http://localhost:8000/v1/opensearch/search",
                json={
                    "query": query,
                    "size": 3,
                    "language": "vi",
                    "highlight_matches": True
                },
                timeout=5
            )
            
            if response.status_code == 200:
                results = response.json()
                print(f"  📄 Found {len(results['hits'])} results")
                
                for hit in results['hits']:
                    faculty = hit.get('faculty', 'N/A')
                    doc_type = hit.get('doc_type', 'N/A') 
                    score = hit['bm25_score']
                    print(f"    • {faculty}/{doc_type} (Score: {score:.2f})")
                    
            else:
                print(f"  ❌ Query failed: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Query error: {e}")

def main():
    """Main function."""
    print("🚀 Sample Data Creator for Vietnamese Hybrid Search")
    print("=" * 60)
    
    # Check if services are running
    import requests
    try:
        response = requests.get("http://localhost:8000/v1/opensearch/health", timeout=5)
        if response.status_code != 200:
            print("❌ OpenSearch service not available. Please start the system first.")
            print("   Run: make start")
            return False
    except:
        print("❌ RAG service not available. Please start the system first.")
        print("   Run: make start") 
        return False
    
    # Index sample data
    if index_sample_data():
        # Test queries
        test_sample_queries()
        
        print("\n" + "=" * 60)
        print("✅ Sample data creation completed!")
        print("\nSample documents created:")
        print("📄 Quy chế tuyển sinh 2024 (CNTT/Regulation)")
        print("📄 Chương trình đào tạo CNTT (CNTT/Syllabus)")
        print("📄 Hướng dẫn sinh viên KHTN (KHTN/Guide)")  
        print("📄 Tài liệu CTDA 2023 (CTDA/Syllabus)")
        print("\nFeatures to test:")
        print("🇻🇳 Vietnamese text analysis")
        print("🏷️  Field filtering (faculty, doc_type, year)")
        print("📍 Character spans for citation")
        print("✨ Vietnamese highlighting")
        print("\nTry running: make test-vietnamese")
        
        return True
    else:
        print("❌ Failed to create sample data")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
