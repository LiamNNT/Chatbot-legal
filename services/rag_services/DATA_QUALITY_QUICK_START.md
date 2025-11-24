# 🚀 QUICK START: Data Quality Improvements

> **Mục đích:** Hướng dẫn nhanh sử dụng các cải tiến về chất lượng dữ liệu

---

## ✅ Đã Hoàn Thành

### 1. Text Cleaning - Loại bỏ TOC Artifacts

**Vấn đề:** Text từ PDF còn dấu chấm dài của mục lục

```
❌ BEFORE: "Điều 7. Chương trình đào tạo ................................ ............ 8"
✅ AFTER:  "Điều 7. Chương trình đào tạo"
```

**Sử dụng:**

```python
from indexing.preprocess.vietnamese_text_cleaner import clean_vietnamese_text

# Tự động
raw_text = "Điều 10. Chế độ học tập ............... 11"
cleaned = clean_vietnamese_text(raw_text)
print(cleaned)  # "Điều 10. Chế độ học tập"
```

**Test:**

```bash
cd services/rag_services
python indexing/preprocess/vietnamese_text_cleaner.py
```

---

### 2. Weaviate Schema V3 - Flattened Metadata

**Vấn đề:** Không thể filter theo chapter, article_number

```python
# ❌ BEFORE - Không được
results = search("học phí", filters={"chapter": "Chương 1"})
# ERROR: metadata_json là string!

# ✅ AFTER - OK
results = collection.query.hybrid(
    query="học phí",
    filters=Filter.by_property("chapter").equal("Chương 1")
)
```

**Tạo Schema V3:**

```bash
cd services/rag_services
python scripts/improve_weaviate_schema.py
```

**Output:**
```
📊 Created collection 'VietnameseDocumentV3'
   - 12 filterable fields
   - chapter, article_number, structure_type
   - KG integration ready
```

---

### 3. Cross-Reference Layer - Neo4j

**Vấn đề:** Graph thiếu liên kết REFERENCES giữa các điều

**Chạy builder:**

```bash
cd services/rag_services
python scripts/build_cross_references.py
```

**Example Output:**
```
🔨 Building cross-references...
   ✓ Article 10 → Article 6
   ✓ Article 15 → Article 25
   ...
   
✅ Created 45 REFERENCES relationships
```

**Verify trong Neo4j Browser:**

```cypher
// Xem cross-references
MATCH (source:Article)-[r:REFERENCES]->(target:Article)
RETURN source.article_number, target.article_number
LIMIT 10

// Multi-hop query
MATCH path = (start:Article {article_number: 10})-[:REFERENCES*..3]->(end:Article)
RETURN path
```

---

## 📋 Các Trường Mới trong Weaviate V3

| Field | Type | Example | Filterable |
|-------|------|---------|-----------|
| `structure_type` | TEXT | "article" | ✅ Yes |
| `chapter` | TEXT | "Chương 1" | ✅ Yes |
| `chapter_title` | TEXT | "QUY ĐỊNH CHUNG" | No |
| `article_number` | INT | 7 | ✅ Yes |
| `article_title` | TEXT | "Chương trình đào tạo" | No |
| `parent_id` | TEXT | "Chương 1" | ✅ Yes |
| `kg_node_id` | TEXT | "quy_dinh_790_article_7" | ✅ Yes |
| `issuer` | TEXT | "Hiệu trưởng" | No |

---

## 🎯 Use Cases

### Use Case 1: Filter by Chapter

```python
from weaviate.classes.query import Filter

results = collection.query.hybrid(
    query="điều kiện tốt nghiệp",
    filters=Filter.by_property("chapter").equal("Chương 5")
)
```

### Use Case 2: Range Query on Article Number

```python
results = collection.query.hybrid(
    query="học phí",
    filters=(
        Filter.by_property("article_number").greater_than(10) &
        Filter.by_property("article_number").less_than(20)
    )
)
```

### Use Case 3: Complex Filter

```python
results = collection.query.hybrid(
    query="sinh viên",
    filters=(
        Filter.by_property("doc_type").equal("regulation") &
        Filter.by_property("structure_type").equal("article") &
        Filter.by_property("chapter").equal("Chương 2")
    ),
    limit=5
)
```

### Use Case 4: Graph Traversal with References

```python
# In Neo4j
query = """
MATCH (article:Article {article_number: 10})
MATCH (article)-[:REFERENCES]->(referenced:Article)
RETURN article.title_vi, referenced.article_number, referenced.title_vi
"""
```

---

## ⏭️ Next Steps

### 1. Re-index Data (Chưa làm)

```bash
# Script này chưa tạo - cần viết
python scripts/reindex_with_improvements.py
```

**Workflow:**
1. Load PDF files
2. Clean với improved cleaner
3. Parse structure
4. Index to Weaviate V3
5. Index to Neo4j with cross-refs

### 2. Test Hybrid Search

```python
# Test filter performance
import time

start = time.time()
results = collection.query.hybrid(
    query="học phí",
    filters=Filter.by_property("chapter").equal("Chương 1")
)
print(f"Time: {time.time() - start:.2f}s")
```

### 3. Implement Tier 2 & 3

- **Tier 2:** Entity extraction (Sinh viên, Giảng viên, etc.)
- **Tier 3:** Rule extraction (if-then logic)

---

## 🐛 Troubleshooting

### Issue: "Collection already exists"

```python
# Delete old collection
client.collections.delete("VietnameseDocumentV3")
# Re-run script
python scripts/improve_weaviate_schema.py
```

### Issue: "No references created"

```bash
# Check if Articles have raw_text
cypher = "MATCH (a:Article) WHERE a.raw_text IS NULL RETURN count(a)"
# If count > 0, need to re-index with text
```

### Issue: "Filter not working"

```python
# Make sure using V3 collection
collection = client.collections.get("VietnameseDocumentV3")
# Not "VietnameseDocument" (old)
```

---

## 📊 Monitoring

### Check Data Quality

```bash
# Weaviate stats
python scripts/weaviate_stats.py

# Neo4j stats  
python scripts/check_neo4j_data.py

# Graph references
cypher: MATCH ()-[r:REFERENCES]->() RETURN count(r)
```

---

## 📞 Support

**Questions?** Check:

1. `DATA_QUALITY_IMPROVEMENT_SUMMARY.md` - Full analysis
2. Test scripts output
3. Neo4j Browser (http://localhost:7474)
4. Weaviate Console (http://localhost:8090)

---

**Last Updated:** Nov 21, 2025  
**Status:** ✅ Ready to use
