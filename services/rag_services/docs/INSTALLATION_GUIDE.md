# Installation Guide - Enhanced Features

## 🚀 Quick Install

### Option 1: Enhanced Mode (Recommended)

Install **pdfplumber** for full table extraction support:

```bash
cd services/rag_services
pip install pdfplumber
```

**Benefits**:
- ✅ Perfect table structure preservation
- ✅ Better multi-column layout handling
- ✅ Export tables to Markdown/JSON
- ✅ More accurate text extraction

### Option 2: Basic Mode (Fallback)

If you only need basic PDF text extraction:

```bash
pip install PyPDF2
```

**Note**: PyPDF2 does NOT preserve table structure

---

## 🧪 Verify Installation

Run the integration test:

```bash
cd services/rag_services
python scripts/test_etl_integration.py
```

Expected output:
```
✅ PDFLoader is using EnhancedPDFLoader (pdfplumber)
✅ EnhancedPDFParser imported successfully
✅ CrossReferenceDetector imported successfully
✅ All tests passed: 5/5

🎉 ALL TESTS PASSED!
```

---

## 📦 What Gets Installed

### With pdfplumber:
```
pdfplumber>=0.10.0
  ├── pdfminer.six>=20221105
  ├── Pillow>=9.1.0
  ├── pypdfium2>=4.10.0
  └── ...
```

### With PyPDF2 (fallback):
```
PyPDF2>=3.0.0
```

---

## ✅ Integration Status

### Already Integrated:

1. **✅ Enhanced PDF Parser**
   - File: `indexing/enhanced_pdf_parser.py`
   - Status: ✅ Created (370 lines)

2. **✅ ETL Pipeline Integration**
   - File: `indexing/graph_etl_pipeline.py`
   - Status: ✅ Updated (replaced PDFLoader)
   - Line: 121-177

3. **✅ Cross-Reference Detector**
   - File: `indexing/cross_reference_detector.py`
   - Status: ✅ Created (480 lines)
   - Tested: ✅ 29 REFERENCES created on QĐ 790

4. **✅ Documentation**
   - Files: 5 markdown files + 1 cypher file
   - Status: ✅ Complete

---

## 🔄 Migration Path

### Before (OLD):
```python
# graph_etl_pipeline.py
class PDFLoader:
    async def load(self, file_path):
        import PyPDF2  # ❌ Old way
        reader = PyPDF2.PdfReader(file_path)
        ...
```

### After (NEW):
```python
# graph_etl_pipeline.py
class PDFLoader:
    def __init__(self):
        from indexing.enhanced_pdf_parser import EnhancedPDFLoader
        self._loader = EnhancedPDFLoader()  # ✅ New way
    
    async def load(self, file_path):
        return await self._loader.load(file_path)
```

### Features Added:
- ✅ Automatic fallback if pdfplumber not available
- ✅ Table extraction with structure preservation
- ✅ Better text extraction quality
- ✅ Backward compatible (same interface)

---

## 🎯 Usage After Installation

### 1. ETL Pipeline (Automatic)

Just run your existing ETL code - it will automatically use enhanced parser:

```python
from indexing.graph_etl_pipeline import GraphETLPipeline

pipeline = GraphETLPipeline(...)
result = await pipeline.run("data/pdfs/")
# ✅ Automatically uses EnhancedPDFLoader
```

### 2. Direct Usage (Advanced)

For custom PDF processing:

```python
from indexing.enhanced_pdf_parser import EnhancedPDFLoader

loader = EnhancedPDFLoader()
result = await loader.load_with_tables(Path("document.pdf"))

print(f"Extracted {result.total_pages} pages")
print(f"Found {result.total_tables} tables")

# Export first table
if result.tables:
    print(result.tables[0].to_markdown())
```

### 3. Cross-Reference Detection

After ETL pipeline runs:

```bash
cd services/rag_services
python indexing/cross_reference_detector.py
```

---

## 🐛 Troubleshooting

### Issue: "pdfplumber not installed"

**Solution**:
```bash
pip install pdfplumber
```

### Issue: "PyPDF2 not available"

**Solution**:
```bash
pip install PyPDF2
```

### Issue: "Import error"

**Check Python path**:
```python
import sys
sys.path.insert(0, '/path/to/services/rag_services')
```

### Issue: Test fails

**Run verbose test**:
```bash
python scripts/test_etl_integration.py -v
```

---

## 📊 Performance Comparison

### pdfplumber vs PyPDF2:

| Feature | pdfplumber | PyPDF2 |
|---------|-----------|--------|
| Text extraction | ✅ Excellent | ✅ Good |
| Table detection | ✅ **Yes** | ❌ No |
| Multi-column | ✅ **Yes** | ⚠️ Partial |
| Speed | ⚠️ Slower (~2x) | ✅ Fast |
| Table structure | ✅ **Preserved** | ❌ Lost |
| Memory usage | ⚠️ Higher | ✅ Low |

**Recommendation**: Use **pdfplumber** for documents with tables/complex layouts

---

## 🎓 Next Steps

After installation:

1. ✅ **Test ETL Pipeline**
   ```bash
   python scripts/test_etl_integration.py
   ```

2. ✅ **Process a PDF with tables**
   ```bash
   python scripts/run_etl.py --input data/qd_790_2022.pdf
   ```

3. ✅ **Run cross-reference detection**
   ```bash
   python indexing/cross_reference_detector.py
   ```

4. ✅ **Query Neo4j**
   - Open: http://localhost:7474
   - Run queries from: `docs/NEO4J_CROSSREF_QUERIES.cypher`

---

## 📚 Documentation

- **Full Guide**: `docs/ENHANCEMENT_PDF_TABLES_CROSSREFS.md`
- **Summary**: `docs/WEEK2_ENHANCEMENTS_COMPLETE.md`
- **Quick Start**: `indexing/CROSS_REFERENCE_README.md`
- **Cypher Queries**: `docs/NEO4J_CROSSREF_QUERIES.cypher`

---

**Last Updated**: November 20, 2025  
**Status**: ✅ Integration complete, ready for use
