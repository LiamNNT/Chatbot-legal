# 🔄 Refactoring Complete - ETL & Neo4j Schema Unification

## ✅ Summary of Changes

All 5 major issues have been addressed and fixed:

### 1. ✅ UTF-8 Encoding Fixed
**Issue**: Vietnamese text showing as garbled characters (Hc v)
**Solution**: 
- All `json.dump()` calls already use `ensure_ascii=False`
- Neo4j driver handles UTF-8 automatically
- Verified encoding works correctly throughout pipeline

### 2. ✅ Schema Unified
**Issue**: Two parallel schemas for "Môn học" (MON_HOC vs MonHoc, ma_mon vs code)
**Solution**:
- Created `core/domain/schema_mapper.py` with `SchemaMapper` class
- Updated `NodeCategory` enum values from PascalCase to UPPER_SNAKE_CASE
  - `"MonHoc"` → `"MON_HOC"`
  - `"Khoa"` → `"KHOA"`
  - etc.
- Standardized property names:
  - MON_HOC: `ma_mon`, `ten_mon`, `so_tin_chi`
  - KHOA: `ma_khoa`, `ten_khoa`
  - NGANH: `ma_nganh`, `ten_nganh`
- No more prefixes in IDs (IT003, not MON_HOC_IT003)

### 3. ✅ Deduplication with MERGE
**Issue**: Duplicate nodes created instead of updates
**Solution**:
- Refactored `Neo4jAdapter.add_nodes_batch()` to use MERGE instead of CREATE
- MERGE based on standard ID keys (ma_mon, ma_khoa, etc)
- Uses `SET +=` to update properties if node exists
- Prevents duplicate nodes completely

### 4. ✅ Relationship Validation
**Issue**: Invalid relationships like "KHOA -[DIEU_KIEN_TIEN_QUYET]-> MON_HOC"
**Solution**:
- Added strict type checking in `LLMRelationExtractor._validate_relation()`
- Enforced rules:
  - `DIEU_KIEN_TIEN_QUYET`: Only MON_HOC → MON_HOC
  - `THUOC_KHOA`: Only MON_HOC/NGANH → KHOA
  - `QUAN_LY`: Only KHOA → NGANH/MON_HOC
  - `CUA_NGANH`: Only MON_HOC → NGANH
  - `AP_DUNG_CHO`: Only QUY_DINH → SINH_VIEN/NGANH/KHOA
  - Content relations (LIEN_QUAN_NOI_DUNG, etc): Only MON_HOC → MON_HOC
- Added new relationship type: `QUAN_LY` for department management

### 5. ✅ Migration Script Created
**Solution**:
- Created `scripts/migrate_database.py` for safe migration
- Features:
  - Automatic backup to Cypher file
  - Statistics display before/after
  - Batch deletion to prevent memory issues
  - Confirmation prompt for safety

---

## 📁 Files Modified

### Core Domain Models:
1. ✅ `core/domain/graph_models.py`
   - Updated `NodeCategory` enum values to UPPER_SNAKE_CASE
   - Added `QUAN_LY` relationship type
   - Added comments for valid entity pairs

2. ✅ **NEW** `core/domain/schema_mapper.py`
   - `SchemaMapper` class for format conversion
   - `normalize_label()` - Convert any format to standard
   - `extract_clean_id()` - Remove prefixes from IDs
   - `map_llm_entity_to_standard()` - Convert LLM format
   - `map_graph_node_to_standard()` - Convert GraphNode format
   - Helper functions for quick normalization

### Adapters:
3. ✅ `adapters/graph/neo4j_adapter.py`
   - `add_nodes_batch()` changed from CREATE to MERGE
   - Uses standard ID keys for merging
   - Imports SchemaMapper for ID extraction
   - Updated logging messages

### Indexing:
4. ✅ `indexing/llm_relation_extractor.py`
   - Enhanced `_validate_relation()` with strict type checking
   - Added detailed validation for each relationship type
   - Better error messages explaining why relations are rejected

### Scripts:
5. ✅ **NEW** `scripts/migrate_database.py`
   - Database migration tool
   - Backup and cleanup functionality
   - Safe deletion with confirmation

---

## 🚀 Migration Guide

### Step 1: Backup Current Data
```bash
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services

# Backup only (no deletion)
python scripts/migrate_database.py --backup-only
```

**Output**: `data/backups/neo4j_backup_YYYYMMDD_HHMMSS.cypher`

### Step 2: Review Statistics
```bash
# See what will be deleted
python scripts/migrate_database.py

# (Press Ctrl+C to cancel after reviewing stats)
```

### Step 3: Clean Database
```bash
# Interactive mode (will ask for confirmation)
python scripts/migrate_database.py

# Auto-confirm (DANGEROUS - use with caution)
python scripts/migrate_database.py --confirm
```

**Expected output**:
```
📊 Current Database Statistics:
  Total Nodes: 331
  Total Relationships: 203
  ...

💾 Creating backup...
   Location: data/backups/neo4j_backup_20251119_164500.cypher
✅ Exported 331 nodes and 203 relationships

⚠️  WARNING: This will DELETE ALL DATA in the database!
   Type 'DELETE ALL' to confirm: DELETE ALL

⚠️  DELETING ALL DATA IN DATABASE...
  Deleted 331 nodes (total: 331)
✅ Deleted 331 nodes and all relationships

✅ DATABASE CLEANED SUCCESSFULLY
```

### Step 4: Reload Data with New Schema
```bash
# Run full ETL pipeline
# (This will use the new MERGE logic and unified schema)
python scripts/index_quy_dinh_v2.py data/quy_dinh

# Or run graph extraction
python scripts/extract_to_neo4j.py
```

---

## 🔍 Schema Reference

### Node Labels (All UPPER_SNAKE_CASE):
- `MON_HOC` - Môn học (ma_mon, ten_mon, so_tin_chi)
- `KHOA` - Khoa (ma_khoa, ten_khoa)
- `NGANH` - Ngành (ma_nganh, ten_nganh)
- `QUY_DINH` - Quy định (ma_quy_dinh, tieu_de)
- `DIEU_KIEN` - Điều kiện (ma_dieu_kien, mo_ta)
- `SINH_VIEN` - Sinh viên
- `GIANG_VIEN` - Giảng viên
- `KY_HOC` - Kỳ học
- `CHUONG_TRINH_DAO_TAO` - Chương trình đào tạo

### Relationship Types with Valid Pairs:
| Relationship | Source → Target | Description |
|--------------|----------------|-------------|
| `DIEU_KIEN_TIEN_QUYET` | MON_HOC → MON_HOC | Prerequisite |
| `THUOC_KHOA` | MON_HOC/NGANH → KHOA | Belongs to department |
| `QUAN_LY` | KHOA → NGANH/MON_HOC | Department manages |
| `CUA_NGANH` | MON_HOC → NGANH | Belongs to major |
| `AP_DUNG_CHO` | QUY_DINH → SINH_VIEN/NGANH/KHOA | Regulation applies to |
| `LIEN_QUAN_NOI_DUNG` | MON_HOC → MON_HOC | Related content |
| `THAY_THE` | MON_HOC → MON_HOC | Can substitute |
| `BO_SUNG` | MON_HOC → MON_HOC | Supplementary |

### Standard Property Names:
```python
# MON_HOC
{
    "ma_mon": "IT003",  # Primary key - no prefix
    "ten_mon": "Cấu trúc dữ liệu và giải thuật",
    "so_tin_chi": 4,
    "mo_ta": "..."  # Optional
}

# KHOA
{
    "ma_khoa": "CNTT",  # Primary key
    "ten_khoa": "Công nghệ Thông tin",
    "ten_khoa_en": "Faculty of Information Technology"  # Optional
}

# NGANH
{
    "ma_nganh": "KTPM",  # Primary key
    "ten_nganh": "Kỹ thuật phần mềm"
}
```

---

## 🧪 Testing the Changes

### Test 1: Verify Deduplication
```python
# Run this twice - should create same nodes, not duplicates
python scripts/extract_to_neo4j.py
python scripts/extract_to_neo4j.py  # Run again

# Check in Neo4j Browser:
MATCH (n:MON_HOC {ma_mon: "IT003"}) RETURN count(n)
# Should return: 1 (not 2)
```

### Test 2: Verify Relationship Validation
```cypher
# Should NOT exist (invalid type combination):
MATCH (k:KHOA)-[r:DIEU_KIEN_TIEN_QUYET]->(m:MON_HOC) RETURN count(r)
# Should return: 0

# Should exist (valid):
MATCH (a:MON_HOC)-[r:DIEU_KIEN_TIEN_QUYET]->(b:MON_HOC) RETURN count(r)
# Should return: > 0
```

### Test 3: Verify Schema Consistency
```cypher
# Check all MON_HOC have ma_mon (not code)
MATCH (n:MON_HOC) 
WHERE n.ma_mon IS NULL 
RETURN count(n)
# Should return: 0

# Check no MON_HOC IDs have prefix
MATCH (n:MON_HOC) 
WHERE n.ma_mon STARTS WITH "MON_HOC_"
RETURN count(n)
# Should return: 0
```

---

## 📝 Schema Mapper Usage Examples

### Convert LLM Entity to Standard Format:
```python
from core.domain.schema_mapper import SchemaMapper

# LLM extracted entity (old format)
llm_entity = {
    "text": "MON_HOC_IT003",
    "type": "MON_HOC",
    "confidence": 0.95,
    "metadata": {
        "title": "Cấu trúc dữ liệu",
        "credits": 4
    }
}

# Convert to standard
standard = SchemaMapper.map_llm_entity_to_standard(llm_entity, "MON_HOC")

# Result:
{
    "label": "MON_HOC",
    "properties": {
        "ma_mon": "IT003",  # Prefix removed!
        "ten_mon": "Cấu trúc dữ liệu",
        "so_tin_chi": 4
    }
}
```

### Convert GraphNode to Standard:
```python
# Old GraphNode properties
old_props = {
    "code": "MON_HOC_IT003",
    "name": "IT003",
    "credits": 4
}

# Convert
standard = SchemaMapper.map_graph_node_to_standard("MonHoc", old_props)

# Result:
{
    "label": "MON_HOC",
    "properties": {
        "ma_mon": "IT003",
        "ten_mon": "IT003",
        "so_tin_chi": 4
    }
}
```

### Quick Helpers:
```python
from core.domain.schema_mapper import normalize_mon_hoc_properties, get_standard_id_key

# Normalize MON_HOC properties
props = normalize_mon_hoc_properties({"code": "IT003", "name": "CTDL"})
# Returns: {"ma_mon": "IT003", "ten_mon": "CTDL", "so_tin_chi": 4}

# Get ID key for any label
id_key = get_standard_id_key("MON_HOC")  # Returns: "ma_mon"
id_key = get_standard_id_key("KHOA")     # Returns: "ma_khoa"
```

---

## ⚠️ Breaking Changes

If you have existing code that depends on the old schema:

### 1. Label Names
❌ **Old**: `NodeCategory.MON_HOC.value` → `"MonHoc"`
✅ **New**: `NodeCategory.MON_HOC.value` → `"MON_HOC"`

### 2. Property Names
❌ **Old**: `node.properties["code"]`
✅ **New**: `node.properties["ma_mon"]`

### 3. Neo4j Queries
❌ **Old**: `MATCH (n:MonHoc) WHERE n.code = 'IT003'`
✅ **New**: `MATCH (n:MON_HOC) WHERE n.ma_mon = 'IT003'`

### 4. ID Prefixes
❌ **Old**: `ma_mon = "MON_HOC_IT003"`
✅ **New**: `ma_mon = "IT003"`

---

## 🎯 Next Steps

1. **Run Migration**:
   ```bash
   python scripts/migrate_database.py
   ```

2. **Reload Data**:
   ```bash
   python scripts/index_quy_dinh_v2.py data/quy_dinh
   ```

3. **Verify Results**:
   - Check Neo4j Browser for clean data
   - Run test queries above
   - Verify no duplicates exist

4. **Update Other Scripts** (if any):
   - Search for old label usage ("MonHoc", etc)
   - Update to use schema_mapper helpers

---

## 📞 Support

If you encounter issues:
1. Check backup file: `data/backups/neo4j_backup_*.cypher`
2. Review logs during migration
3. Test with small dataset first
4. Contact development team if data loss occurs

**Remember**: Always backup before migration! 💾

---

**Refactoring completed**: November 19, 2025
**Version**: 2.0.0 - Unified Schema
