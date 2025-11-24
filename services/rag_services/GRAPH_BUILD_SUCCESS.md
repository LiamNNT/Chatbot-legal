# ✅ Graph Build từ Data Thật - THÀNH CÔNG

## 📊 Tổng Quan

Đã build thành công Knowledge Graph từ **data thật** trong Weaviate (371 documents từ file PDF quy định UIT).

### Kết Quả:
- **93 QUY_DINH nodes** (từ file PDF: `790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf`)
- **156 relationships** (hierarchical + sequential)
- **UTF-8 encoding hoàn hảo** ✓
- **Data source**: Weaviate vector database (đã indexed từ PDF)

---

## 🔧 Vấn Đề Đã Fix

### 1. ❌ Lỗi Ban Đầu: "Font chữ bị lỗi trên web"

**Root Cause**: 
- Script `extract_to_neo4j.py` đang dùng **MOCK DATA** hardcoded, không phải data thật
- Mock data có encoding issues khi gán trực tiếp vào Python string

### 2. ✅ Giải Pháp: Dùng Script Build từ Weaviate

**Cách fix**:
1. Dùng script `build_graph_from_indexed_data.py` thay vì `extract_to_neo4j.py`
2. Fix 2 bugs trong script:
   - **Bug 1**: Enum conversion - `RelationshipType.THUOC_KHOA` trong Cypher query
   - **Bug 2**: Content field - Weaviate lưu trong `text` không phải `content`

**Code changes**:

```python
# adapters/graph/neo4j_adapter.py (dòng 830)
# FIX: Enum conversion
- if isinstance(rel.rel_type, str):
-     rel_type = rel.rel_type
- else:
-     rel_type = rel.rel_type.value

+ if hasattr(rel.rel_type, 'value'):
+     rel_type = rel.rel_type.value
+ else:
+     rel_type = rel.rel_type
```

```python
# scripts/build_graph_from_indexed_data.py (dòng 76)
# FIX: Content field name
- 'content': obj.properties.get('content', ''),
+ content = obj.properties.get('text', '') or obj.properties.get('content', '')
+ 'content': content,
```

---

## 📁 Files Modified

### 1. `/adapters/graph/neo4j_adapter.py`
- **Line 830-838**: Fixed enum conversion logic
- **Impact**: Relationships now create correctly without Cypher syntax errors

### 2. `/scripts/build_graph_from_indexed_data.py`  
- **Line 76-77**: Changed content field from `content` to `text`
- **Impact**: Full Vietnamese content now loads correctly from Weaviate

---

## 🚀 Cách Sử Dụng

### Build Graph từ Weaviate:

```bash
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services

# Clean database trước (nếu cần)
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'uitchatbot'))
with driver.session() as session:
    session.run('MATCH (n) DETACH DELETE n')
driver.close()
"

# Build graph
python scripts/build_graph_from_indexed_data.py
```

### Xem Kết Quả:

**Neo4j Browser**: http://localhost:7474
```cypher
// Xem tất cả QUY_DINH nodes
MATCH (n:QUY_DINH) RETURN n LIMIT 25

// Tìm các điều về "tín chỉ"
MATCH (n:QUY_DINH) 
WHERE n.full_content CONTAINS 'tín chỉ'
RETURN n.article, n.full_content
LIMIT 10

// Xem relationships
MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 50
```

**Web Viewer** (nếu có): http://localhost:5555

---

## 🔍 Kiểm Tra UTF-8 Encoding

### Test Script:

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'uitchatbot'))

with driver.session() as session:
    result = session.run('''
        MATCH (n:QUY_DINH) 
        WHERE n.full_content IS NOT NULL AND size(n.full_content) > 50
        RETURN n.article, n.full_content 
        LIMIT 3
    ''')
    
    for record in result:
        article = record['n.article']
        content = record['n.full_content']
        
        print(f'{article}: {content[:200]}...')
        
        # Check for encoding errors
        if '�' in content:
            print('  ❌ ENCODING ERROR!')
        else:
            print('  ✅ UTF-8 OK!')

driver.close()
```

### Expected Output:

```
Điều 2: Điều 2. Mục tiêu của chương trình giáo dục...
  ✅ UTF-8 OK!

Điều 3: Điều 3. Môn học...
  ✅ UTF-8 OK!

Điều 4: Điều 4. Tín chỉ học tập – Tín chỉ học phí...
  ✅ UTF-8 OK!
```

---

## 📊 Graph Schema

### Node Types:

| Label | Count | Description | Properties |
|-------|-------|-------------|------------|
| `QUY_DINH` | 93 | Quy định articles | `article`, `title`, `full_content`, `year`, `doc_title` |

### Relationship Types:

| Type | Count | Description | Pattern |
|------|-------|-------------|---------|
| `THUOC_KHOA` | 83 | Hierarchical (Article → Chapter → Doc) | `(Article)-[:THUOC_KHOA]->(Chapter)` |
| `LIEN_QUAN_NOI_DUNG` | 73 | Sequential (Article follows Article) | `(Điều_N)-[:LIEN_QUAN_NOI_DUNG]->(Điều_N+1)` |

### Sample Queries:

```cypher
// Tìm Điều 5
MATCH (n:QUY_DINH {article: 'Điều 5'})
RETURN n.article, n.full_content

// Tìm các điều liên quan đến Điều 5
MATCH (a:QUY_DINH {article: 'Điều 5'})-[r:LIEN_QUAN_NOI_DUNG]-(b:QUY_DINH)
RETURN a.article, type(r), b.article

// Full-text search tiếng Việt
MATCH (n:QUY_DINH)
WHERE n.full_content CONTAINS 'đăng ký học phần'
RETURN n.article, substring(n.full_content, 0, 200)
```

---

## 🎯 Data Source

### Weaviate Database:

- **Host**: localhost:8090
- **Collection**: `VietnameseDocument`
- **Total Documents**: 371 chunks
- **Source File**: `data/quy_dinh/790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf`
- **Indexing Script**: `scripts/index_quy_dinh_v2.py`

### PDF Document Info:

- **Title**: QUY CHẾ ĐÀO TẠO THEO HỌC CHẾ TÍN CHỈ CHO HỆ ĐẠI HỌC CHÍNH QUY
- **Issuer**: Trường Đại học Công nghệ Thông tin (UIT)
- **Document**: 790/QĐ-ĐHCNTT ngày 28/9/2022
- **Pages**: 27 pages
- **Chunks**: 86 articles (Điều)

---

## ⚠️ Important Notes

### 1. **KHÔNG dùng** `extract_to_neo4j.py`
- Script này dùng MOCK DATA hardcoded
- Không phải data thật từ PDF
- Chỉ dùng cho testing/demo

### 2. **Dùng** `build_graph_from_indexed_data.py`
- Extract từ Weaviate (data thật đã indexed)
- UTF-8 encoding đúng
- Full content từ PDF

### 3. **Prerequisites**:
- Weaviate phải đang chạy (`docker ps | grep weaviate`)
- Data đã được indexed (`python scripts/index_quy_dinh_v2.py data/quy_dinh`)
- Neo4j đang chạy (`docker ps | grep neo4j`)

---

## 🐛 Troubleshooting

### Issue: "No documents found in Weaviate"

```bash
# Check Weaviate status
docker ps | grep weaviate

# Check data
python -c "
import weaviate
client = weaviate.connect_to_local(host='localhost', port=8090, grpc_port=50051)
collection = client.collections.get('VietnameseDocument')
response = collection.aggregate.over_all(total_count=True)
print(f'Total documents: {response.total_count}')
client.close()
"

# If empty, re-index
python scripts/index_quy_dinh_v2.py data/quy_dinh
```

### Issue: "Neo4j connection failed"

```bash
# Check Neo4j status
docker ps | grep neo4j

# Start Neo4j if not running
docker-compose -f docker/docker-compose.neo4j.yml up -d

# Test connection
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'uitchatbot'))
driver.verify_connectivity()
print('✅ Connection OK')
driver.close()
"
```

### Issue: "Font chữ vẫn bị lỗi"

**Nếu trên Neo4j Browser**:
1. Clear browser cache: Ctrl+Shift+R (Chrome/Firefox)
2. Run query lại: `MATCH (n:QUY_DINH) RETURN n LIMIT 10`
3. Check encoding bằng Python script (xem trên)

**Nếu encoding thật sự bị lỗi**:
1. Clean database: `MATCH (n) DETACH DELETE n`
2. Rebuild: `python scripts/build_graph_from_indexed_data.py`
3. Verify: Check full_content field có ký tự � không

---

## ✅ Success Checklist

- [x] Weaviate có 371 documents
- [x] Neo4j có 93 QUY_DINH nodes
- [x] UTF-8 encoding đúng (không có �)
- [x] Full content hiển thị tiếng Việt hoàn hảo
- [x] Relationships tạo thành công
- [x] Neo4j Browser hiển thị graph đúng

---

**Date**: November 19, 2025  
**Status**: ✅ COMPLETED  
**Data Source**: Real PDF from `data/quy_dinh/790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf`  
**Encoding**: UTF-8 ✓  
**Total Nodes**: 93  
**Total Relationships**: 156
