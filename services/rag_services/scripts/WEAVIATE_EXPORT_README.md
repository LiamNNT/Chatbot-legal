# Weaviate Data Export Scripts

Scripts để quản lý và xuất dữ liệu từ Weaviate vector database.

## 📁 Scripts

### 1. `export_weaviate_to_json.py`
Xuất toàn bộ hoặc một phần dữ liệu từ Weaviate ra file JSON.

**Tính năng:**
- ✅ Xuất tất cả collections hoặc chỉ một collection cụ thể
- ✅ Hỗ trợ giới hạn số lượng documents
- ✅ Có thể bao gồm hoặc loại bỏ vector embeddings
- ✅ Xem summary của file export đã tạo
- ✅ Output JSON đẹp, dễ đọc với metadata đầy đủ

**Cách sử dụng:**

```bash
# Xuất tất cả collections
python scripts/export_weaviate_to_json.py

# Xuất collection cụ thể
python scripts/export_weaviate_to_json.py --class-name VietnameseDocument

# Xuất với giới hạn (100 documents đầu tiên)
python scripts/export_weaviate_to_json.py --limit 100

# Xuất kèm vector embeddings (file sẽ rất lớn!)
python scripts/export_weaviate_to_json.py --include-vector

# Xuất ra file tùy chọn
python scripts/export_weaviate_to_json.py --output backups/weaviate_2024_11_21.json

# Xem summary của file export
python scripts/export_weaviate_to_json.py --summary
```

**Output mẫu:**

```json
{
  "export_timestamp": "2025-11-21T16:13:09.195078",
  "weaviate_url": "http://localhost:8090",
  "collections": {
    "VietnameseDocument": {
      "count": 371,
      "objects": [
        {
          "uuid": "00b4eaf2-f4c1-43d0-9075-14dc09dda72c",
          "properties": {
            "article": "Điều 7",
            "doc_type": "regulation",
            "text": "...",
            "chunk_id": "...",
            "metadata_json": "{...}"
          },
          "metadata": {}
        }
      ]
    }
  },
  "summary": {
    "total_collections": 1,
    "total_objects": 371,
    "include_vector": false
  }
}
```

### 2. `weaviate_stats.py`
Xem thống kê nhanh về dữ liệu trong Weaviate (không cần xuất file).

**Tính năng:**
- ✅ Thống kê số lượng documents
- ✅ Phân loại theo doc_type, faculty, language
- ✅ Top 10 chapters, sections, articles (chế độ detailed)
- ✅ Hiển thị màu sắc đẹp mắt

**Cách sử dụng:**

```bash
# Xem thống kê cơ bản
python scripts/weaviate_stats.py

# Xem thống kê chi tiết (top 10 mọi thứ)
python scripts/weaviate_stats.py --detailed
```

**Output mẫu:**

```
======================================================================
                     📊 Weaviate Quick Statistics                      
======================================================================

Collections: 1
  VietnameseDocument

Collection: VietnameseDocument
──────────────────────────────────────────────────────────────────────
  Total documents: 371

  Document Types:
    - regulation: 371

  Faculties:
    - UIT: 371

  Languages:
    - vi: 371

  Chapters (top 10):
    - Chương 2: 120
    - Chương 3: 72
    - Chương 1: 52
```

## 🔧 Cấu hình

Scripts đọc từ file `.env`:

```env
WEAVIATE_URL=http://localhost:8090
WEAVIATE_API_KEY=  # Optional, để trống nếu local
WEAVIATE_CLASS_NAME=VietnameseDocument
```

## 📦 Dependencies

```bash
pip install weaviate-client python-dotenv
```

## 🎯 Use Cases

### Backup dữ liệu
```bash
# Tạo backup toàn bộ (không bao gồm vectors)
python scripts/export_weaviate_to_json.py \
  --output backups/weaviate_backup_$(date +%Y%m%d).json

# Tạo backup đầy đủ (bao gồm cả vectors)
python scripts/export_weaviate_to_json.py \
  --include-vector \
  --output backups/weaviate_full_backup_$(date +%Y%m%d).json
```

### Debug & Analysis
```bash
# Xem thống kê nhanh
python scripts/weaviate_stats.py

# Xuất sample 100 docs để kiểm tra
python scripts/export_weaviate_to_json.py --limit 100 --output samples/sample_100.json

# Xem summary của backup cũ
python scripts/export_weaviate_to_json.py --output backups/old_backup.json --summary
```

### Sharing data
```bash
# Xuất collection cụ thể để share
python scripts/export_weaviate_to_json.py \
  --class-name VietnameseDocument \
  --output data_export/vietnamese_docs.json
```

## 📊 Kích thước file

- **Không có vectors**: ~300 KB cho 371 documents
- **Có vectors**: ~50-100 MB cho 371 documents (tùy embedding model)

## ⚠️ Lưu ý

1. **Include vectors**: Chỉ dùng khi thực sự cần, file sẽ rất lớn
2. **Large collections**: Với >10K documents, nên dùng `--limit` để test trước
3. **Memory**: Script load tất cả vào RAM, cẩn thận với collections lớn
4. **Version warning**: Weaviate client có thể hiển thị deprecation warning (bỏ qua được)

## 🚀 Quick Start

```bash
# 1. Xem có bao nhiêu dữ liệu
python scripts/weaviate_stats.py

# 2. Xuất toàn bộ ra JSON
python scripts/export_weaviate_to_json.py

# 3. Xem file vừa xuất
python scripts/export_weaviate_to_json.py --summary

# 4. Open file với jq (nếu có)
cat data/weaviate_export.json | jq '.summary'
```

## 📝 License

MIT License - Free to use and modify
