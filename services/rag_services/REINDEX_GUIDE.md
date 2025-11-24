# 🔄 Re-indexing Guide - Data Quality Improvements

> **Script:** `scripts/reindex_with_improvements.py`  
> **Purpose:** Re-index all PDFs with improved text cleaning and Weaviate V3 schema

---

## 📋 Prerequisites

### 1. Weaviate V3 Schema Created

```bash
# Create V3 schema first!
python scripts/improve_weaviate_schema.py
```

Expected output:
```
✅ Created collection 'VietnameseDocumentV3'
   - 12 filterable fields
   - Flattened metadata ready
```

### 2. Services Running

```bash
# Weaviate
docker ps | grep weaviate  # Should be running on port 8090

# Neo4j (optional for now)
docker ps | grep neo4j  # Should be running on port 7687
```

### 3. PDF Files Ready

```bash
# Check PDFs exist
ls -la services/rag_services/data/quy_dinh/*.pdf
```

---

## 🚀 Usage

### Option 1: Dry Run (Recommended First)

Test without actually indexing:

```bash
cd services/rag_services
python scripts/reindex_with_improvements.py --dry-run
```

**What it does:**
- ✅ Extract text from PDFs
- ✅ Apply improved text cleaning
- ✅ Parse legal structure
- ✅ Show what would be indexed
- ❌ **Does NOT** actually index

**Output:**
```
📦 Processing PDF 1/5
📄 Processing: 790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf
  ✓ Extracted 150000 chars from 27 pages
  ✓ Applied improved text cleaning
  ✓ Document metadata:
    Title: QUY CHẾ ĐÀO TẠO...
    Doc #: 790-qd-dhcntt
  ✓ Parsed 86 structural elements
  ✓ Created 86 Weaviate objects (V3 schema)
  🔍 DRY RUN: Would index 86 objects
```

---

### Option 2: Full Re-indexing

Actually index to Weaviate V3:

```bash
cd services/rag_services
python scripts/reindex_with_improvements.py
```

**What it does:**
- ✅ Process all PDFs
- ✅ Clean text (TOC artifacts removed!)
- ✅ Index to `VietnameseDocumentV3`
- ✅ Verify data quality

**Duration:** ~2-5 minutes for 5 PDFs

---

### Option 3: Verify Only

Check existing data quality:

```bash
python scripts/reindex_with_improvements.py --verify-only
```

**Checks:**
- TOC artifacts in text
- Flattened metadata presence
- Sample object structure

---

## 📊 Expected Output

### During Processing

```
================================================================================
🚀 RE-INDEXING WITH DATA QUALITY IMPROVEMENTS
================================================================================
✅ Using collection: VietnameseDocumentV3

================================================================================
📦 Processing PDF 1/5
================================================================================

📄 Processing: 790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf
  ✓ Extracted 150234 chars from 27 pages
  ✓ Applied improved text cleaning
  ✓ Document metadata:
    Title: QUY CHẾ ĐÀO TẠO THEO HỌC CHẾ TÍN CHỈ...
    Doc #: 790-qd-dhcntt
  ✓ Parsed 86 structural elements
  ✓ Created 86 Weaviate objects (V3 schema)
  ✅ Indexed 86 objects to Weaviate
  ✅ Success: 86 chunks

[... other PDFs ...]
```

### Summary

```
================================================================================
📊 RE-INDEXING SUMMARY
================================================================================
Duration: 145.3s
PDFs processed: 5
Elements parsed: 430
Weaviate indexed: 430
PDF errors: 0
Weaviate errors: 0

✅ Re-indexing complete!
```

### Verification

```
================================================================================
🔍 VERIFYING DATA QUALITY
================================================================================

📊 Weaviate Collection: VietnameseDocumentV3
Total objects: 5 (sample)

✅ Quality Checks:
  TOC artifacts found: 0/5  ✅ CLEAN!
  Flattened metadata: 5/5   ✅ ALL HAVE METADATA!

📄 Sample Object:
  Text preview: Điều 7. Chương trình đào tạo
                1. Chương trình đào tạo là văn bản...
  Chapter: Chương 1
  Article: Điều 7
  Structure type: article
```

---

## 🎯 Key Improvements Applied

### 1. Text Cleaning

**Before:**
```
"Điều 7. Chương trình đào tạo ................................ ............ 8"
```

**After:**
```
"Điều 7. Chương trình đào tạo"
```

### 2. Flattened Metadata

**Before (V2):**
```json
{
  "metadata_json": "{\"chapter\": \"Chương 1\", \"article_number\": 7}"
}
```

**After (V3):**
```json
{
  "chapter": "Chương 1",
  "article_number": 7,
  "structure_type": "article",
  "metadata_json": "..." // Still kept for backward compatibility
}
```

### 3. Filterable Fields

Now you can do:
```python
# Filter by chapter
results = collection.query.hybrid(
    query="học phí",
    filters=Filter.by_property("chapter").equal("Chương 1")
)

# Range query on article number
results = collection.query.hybrid(
    query="quy định",
    filters=(
        Filter.by_property("article_number").greater_than(10) &
        Filter.by_property("article_number").less_than(20)
    )
)
```

---

## 🐛 Troubleshooting

### Error: "Collection does not exist"

```bash
# Create V3 schema first
python scripts/improve_weaviate_schema.py
```

### Error: "Cannot connect to Weaviate"

```bash
# Check if Weaviate is running
docker ps | grep weaviate

# Start if not running
docker-compose -f docker/docker-compose.weaviate.yml up -d

# Wait 30 seconds for startup
sleep 30
```

### Error: "PyPDF2 not found"

```bash
pip install PyPDF2
```

### Error: "No PDF files found"

```bash
# Check data directory
ls -la services/rag_services/data/quy_dinh/

# Or specify custom directory
python scripts/reindex_with_improvements.py --data-dir /path/to/pdfs
```

---

## 📊 Monitoring Progress

### Check Weaviate Stats

```bash
python scripts/weaviate_stats.py
```

### Query Weaviate Directly

```python
from infrastructure.store.vector.weaviate_store import get_weaviate_client

client = get_weaviate_client("http://localhost:8090")
collection = client.collections.get("VietnameseDocumentV3")

# Count objects
response = collection.query.fetch_objects(limit=1)
print(f"Total: {len(response.objects)}")

# Sample query
response = collection.query.fetch_objects(
    limit=5,
    filters=Filter.by_property("structure_type").equal("article")
)

for obj in response.objects:
    props = obj.properties
    print(f"Article {props.get('article_number')}: {props.get('article_title')}")
```

---

## 🔄 Re-running

### Clear Old Data

If you want to start fresh:

```python
# In Python
from infrastructure.store.vector.weaviate_store import get_weaviate_client

client = get_weaviate_client("http://localhost:8090")
client.collections.delete("VietnameseDocumentV3")

# Re-create schema
# python scripts/improve_weaviate_schema.py

# Re-index
# python scripts/reindex_with_improvements.py
```

---

## 📈 Performance Tips

### 1. Process Specific PDFs

```bash
# Put only specific PDFs in a temp directory
mkdir temp_pdfs
cp data/quy_dinh/specific.pdf temp_pdfs/

# Index only those
python scripts/reindex_with_improvements.py --data-dir temp_pdfs
```

### 2. Monitor Memory

```bash
# Watch memory usage
watch -n 1 'ps aux | grep python | grep reindex'
```

### 3. Batch Size

The script processes one PDF at a time sequentially. For large datasets, consider:
- Processing in batches
- Parallel processing (requires script modification)

---

## ✅ Success Criteria

After re-indexing, verify:

- [ ] All PDFs processed without errors
- [ ] No TOC artifacts in sample texts
- [ ] All objects have flattened metadata
- [ ] Filter queries work correctly
- [ ] Text quality improved (spot check)

---

## 🔗 Related

- `improve_weaviate_schema.py` - Create V3 schema
- `build_cross_references.py` - Add Neo4j cross-references
- `DATA_QUALITY_README.md` - Full documentation

---

**Last Updated:** Nov 21, 2025  
**Version:** 1.0
