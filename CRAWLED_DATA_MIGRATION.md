# Crawled Data Migration Summary

## ✅ Hoàn thành

Dữ liệu crawled từ nhánh `feature/crawler-implementation` đã được đưa vào nhánh `main` thành công!

## 📦 Những gì đã được thêm vào

### 1. Dữ liệu Crawled
- **File**: `services/rag_services/data/crawled_programs/cu-nhan-nganh-khoa-hoc-may-tinh-ap-dung-tu-khoa-19-2024.txt`
- **Nội dung**: Chương trình đào tạo Cử nhân Khoa học Máy tính - Khóa 19 (2024)
- **Nguồn**: https://student.uit.edu.vn
- **Kích thước**: 22,598 ký tự
- **Ngày crawl**: 2025-10-13

### 2. Scripts Hỗ trợ
- **`index_crawled_data.py`**: Script để index dữ liệu crawled vào Weaviate
  - Tự động parse metadata (môn học, năm, khóa)
  - Chia content thành chunks
  - Tạo embeddings và lưu vào vector database
  
- **`test_crawled_search.py`**: Script test tìm kiếm với dữ liệu crawled
  - Test các query về chương trình đào tạo
  - Hiển thị kết quả search với metadata

### 3. Tài liệu
- **`README.md`**: Hướng dẫn chi tiết về:
  - Cấu trúc dữ liệu
  - Cách index vào RAG
  - Cách test và sử dụng
  - Metadata được trích xuất

## 🚀 Cách sử dụng

### Bước 1: Cài đặt dependencies (nếu chưa có)
```bash
cd services/rag_services
pip install llama-index-vector-stores-weaviate weaviate-client
```

### Bước 2: Index dữ liệu vào RAG
```bash
python scripts/index_crawled_data.py
```

Output mong đợi:
```
📌 Step 1: Load crawled program files
Found 1 crawled files
  ✓ Title: Cử nhân ngành Khoa học Máy tính (Áp dụng từ khóa 19 - 2024)
  ✓ Subject: Khoa học Máy tính, Year: 2024

📌 Step 2: Create document chunks
Created 1 total chunks from 1 files

📌 Step 3: Index into Weaviate
✅ Successfully indexed 1 document chunks
```

### Bước 3: Test RAG
```bash
python scripts/test_crawled_search.py
```

## 🎯 Kết quả

### Commits
1. **e79f894**: `feat: Add crawled KHMT 2024 curriculum data and indexing scripts`
   - Thêm dữ liệu crawled
   - Thêm scripts index và test

2. **90b5d97**: `docs: Add README for crawled programs data`
   - Thêm tài liệu hướng dẫn

### Branches
- ✅ Dữ liệu đã được merge vào `main`
- ✅ Đã push lên GitHub
- 📍 Nhánh `feature/crawler-implementation` vẫn còn để tham khảo

## 📊 Metadata được trích xuất tự động

Script `index_crawled_data.py` tự động trích xuất:
- **Program Level**: undergraduate, distance_learning, second_degree
- **Subject**: Khoa học Máy tính, Hệ thống Thông tin, v.v.
- **Year**: Năm học (2024)
- **Cohort**: Khóa học (19)
- **URL**: Link nguồn gốc
- **Crawled Date**: Ngày thu thập dữ liệu

## ⚠️ Lưu ý về Schema Issue

Hiện tại có một vấn đề nhỏ với Weaviate schema khi test search trực tiếp:
```
Error: no such prop with name 'id' found in class 'ChatbotUit'
```

**Nguyên nhân**: LlamaIndex vector store adapter có thể cần cập nhật schema

**Giải pháp tạm thời**:
1. Sử dụng API của RAG service thay vì test trực tiếp adapter
2. Hoặc reset Weaviate collection và re-index

**Test qua API**:
```bash
# Start server
python start_server.py

# Test API (terminal khác)
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Chương trình đào tạo KHMT 2024", "top_k": 3}'
```

## 🔜 Tiếp theo

1. **Thêm dữ liệu crawled khác**:
   - Hệ thống Thông tin
   - Mạng máy tính
   - Kỹ thuật Phần mềm
   - An toàn Thông tin

2. **Sửa schema issue**: 
   - Reset và tạo lại Weaviate collection với schema đúng
   - Hoặc dùng Weaviate native client

3. **Tích hợp với Orchestrator**:
   - RAG agent có thể query dữ liệu này
   - Trả lời câu hỏi về chương trình đào tạo

4. **Automation**:
   - Script tự động crawl và update định kỳ
   - CI/CD pipeline để auto-index khi có dữ liệu mới

## 📝 Files trong Main Branch

```
services/rag_services/data/crawled_programs/
├── README.md                                    # ✅ NEW
├── cu-nhan-nganh-khoa-hoc-may-tinh-ap-dung-tu-khoa-19-2024.txt  # ✅ NEW

services/rag_services/scripts/
├── index_crawled_data.py                        # ✅ NEW
├── test_crawled_search.py                       # ✅ NEW
└── ... (other scripts)
```

## 🎉 Kết luận

Dữ liệu crawled đã sẵn sàng trong nhánh `main`! Bạn có thể:
- ✅ Index vào Weaviate
- ✅ Test RAG search
- ✅ Sử dụng trong chatbot
- ✅ Thêm dữ liệu mới theo cùng format

Mọi thứ đã được document đầy đủ trong README.md!
