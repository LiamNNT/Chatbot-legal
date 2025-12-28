# LlamaIndex Extraction Pipeline Guide

## Overview

This document describes the integration of LlamaParse and PropertyGraphIndex for knowledge graph extraction, replacing the manual 2-stage hybrid extraction pipeline.

## Architecture Comparison

### Before (Manual 2-Stage Pipeline)

```
hybrid_extractor.py
├── Stage 1: StructureExtractor (VLM)
│   ├── PDF → Images (pdf2image)
│   ├── Images → VLM API (GPT-4o Vision)
│   ├── Parse JSON response
│   └── Merge split tables manually
└── Stage 2: SemanticExtractor (LLM)
    ├── Article text → LLM API
    ├── Parse entities/relations
    └── convert_to_graph_models()
```

**Problems:**
- Manual table merging logic (complex, error-prone)
- Split tables across pages not handled well
- Custom prompts for each extraction stage
- Manual entity/relation ID management

### After (LlamaIndex Pipeline)

```
llamaindex_extractor.py
├── Stage 1: LlamaParseDocumentParser
│   ├── PDF → LlamaParse API
│   ├── Automatic table extraction
│   ├── Structure preservation
│   └── Chunking with article boundaries
└── Stage 2: PropertyGraphKGExtractor
    ├── Chunks → PropertyGraphIndex
    ├── SchemaLLMPathExtractor
    ├── Automatic entity/relation extraction
    └── Direct Neo4j integration (optional)
```

**Benefits:**
- LlamaParse handles complex tables automatically
- Split tables merged correctly
- PropertyGraphIndex automates KG extraction
- Schema-guided extraction with validation
- Direct Neo4j integration

## Quick Start

### Enable LlamaIndex Extraction

```bash
# In .env file
USE_LLAMAINDEX_EXTRACTION=true
LLAMA_CLOUD_API_KEY=your_llamaparse_api_key
```

### Basic Usage

```python
from app.core.extraction.llamaindex_extractor import LlamaIndexExtractionService
from pathlib import Path

# Create service from environment
service = LlamaIndexExtractionService.from_env()

# Extract KG from PDF
result = await service.extract_from_pdf(Path("regulation.pdf"))

# Get entities and relations
print(f"Entities: {len(result.entities)}")
print(f"Relations: {len(result.relations)}")

# Convert to GraphNode/GraphRelationship (compatible with existing code)
nodes, relationships = result.to_graph_models()
```

### CLI Usage

```bash
cd services/rag_services
python -m app.core.extraction.llamaindex_extractor \
    --pdf path/to/document.pdf \
    --output result.json
```

## Configuration

### Environment Variables

```bash
# LlamaParse (Required)
LLAMA_CLOUD_API_KEY=llx-xxxxxx

# Neo4j (Optional - for direct storage)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLM for extraction
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-xxxxxx
# OR
OPENROUTER_API_KEY=sk-or-xxxxxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

### Programmatic Configuration

```python
from app.core.extraction.llamaindex_extractor import (
    ExtractionConfig,
    LlamaIndexExtractionService
)

config = ExtractionConfig(
    llama_cloud_api_key="llx-xxx",
    llm_model="gpt-4o-mini",
    llm_api_key="sk-xxx",
    chunk_size=1024,
    chunk_overlap=200,
    extract_tables_separately=True
)

service = LlamaIndexExtractionService(config)
```

## Components

### 1. LlamaParseDocumentParser

Handles PDF parsing using LlamaParse cloud service.

```python
from app.core.extraction.llamaindex_extractor import (
    LlamaParseDocumentParser,
    ExtractionConfig
)

parser = LlamaParseDocumentParser(config)

# Parse PDF
parsed_doc = await parser.parse_pdf(Path("document.pdf"))

print(f"Pages: {parsed_doc.pages}")
print(f"Tables: {len(parsed_doc.tables)}")
print(f"Chunks: {len(parsed_doc.chunks)}")
```

**Features:**
- Automatic table detection and formatting
- Vietnamese language support
- GPT-4o mode for complex documents
- Markdown output with structure preservation

### 2. PropertyGraphKGExtractor

Extracts entities and relations using LlamaIndex PropertyGraphIndex.

```python
from app.core.extraction.llamaindex_extractor import (
    PropertyGraphKGExtractor,
    ExtractionConfig
)

extractor = PropertyGraphKGExtractor(config)

# Extract from chunks
entities, relations = await extractor.extract_from_chunks(
    chunks=parsed_doc.chunks,
    document_id="regulation_790"
)
```

**Features:**
- Schema-guided extraction
- Automatic entity deduplication
- Relation evidence preservation
- Fallback to direct LLM when PropertyGraphIndex unavailable

### 3. ExtractionResult

Unified result container with graph model conversion.

```python
result = ExtractionResult(
    document_id="doc_1",
    parsed_document=parsed_doc,
    entities=entities,
    relations=relations
)

# Convert to existing graph models
from core.domain.graph_models import GraphNode, GraphRelationship

nodes, rels = result.to_graph_models()

# nodes: List[GraphNode]
# rels: List[GraphRelationship]
```

## Entity and Relation Types

### Entity Types

| Type | Description | Example |
|------|-------------|---------|
| MON_HOC | Course/Subject | "Anh văn 1", "Toán cao cấp" |
| QUY_DINH | Regulation | "Điều 5", "Quy chế đào tạo" |
| DIEU_KIEN | Condition | "đăng ký tối thiểu 12 tín chỉ" |
| CHUNG_CHI | Certificate | "IELTS", "TOEIC" |
| DIEM_SO | Score | "6.0", "450 điểm" |
| DO_KHO | Proficiency level | "B1", "Intermediate" |
| DOI_TUONG | Target group | "sinh viên CLC", "hệ chính quy" |
| THOI_GIAN | Time period | "2 năm", "học kỳ 1" |
| SO_LUONG | Quantity | "12 tín chỉ", "70 sinh viên" |

### Relation Types

| Type | Description | Example |
|------|-------------|---------|
| YEU_CAU | Requires | Quy định -> yêu cầu -> Điều kiện |
| AP_DUNG_CHO | Applies to | Quy định -> áp dụng -> Đối tượng |
| DAT_DIEM | Achieves score | IELTS -> đạt -> 6.0 |
| TUONG_DUONG | Equivalent | IELTS 6.0 -> tương đương -> TOEFL 72 |
| MIEN_GIAM | Exempts | Chứng chỉ -> miễn -> Môn học |
| SUA_DOI | Amends | QĐ mới -> sửa đổi -> QĐ cũ |
| THAY_THE | Replaces | QĐ mới -> thay thế -> QĐ cũ |
| DIEU_KIEN_TIEN_QUYET | Prerequisite | Toán 2 -> yêu cầu -> Toán 1 |

## Migration from hybrid_extractor

### Old Code

```python
from app.core.extraction.hybrid_extractor import run_pipeline

result, nodes, rels = run_pipeline(
    pdf_path="document.pdf",
    output_path="result.json"
)
```

### New Code

```python
from app.core.extraction.llamaindex_extractor import run_llamaindex_pipeline

result, nodes, rels = run_llamaindex_pipeline(
    pdf_path="document.pdf",
    output_path="result.json"
)
```

### Automatic Switching

Set `USE_LLAMAINDEX_EXTRACTION=true` to use the new pipeline automatically.

## Testing

```bash
cd services/rag_services

# Run extraction tests
pytest tests/test_llamaindex_extraction.py -v

# Run with coverage
pytest tests/test_llamaindex_extraction.py -v --cov=app.core.extraction
```

## Troubleshooting

### LlamaParse API Key

```
Error: LLAMA_CLOUD_API_KEY not set
```

Get your API key from [LlamaCloud](https://cloud.llamaindex.ai/) and set it:

```bash
export LLAMA_CLOUD_API_KEY=llx-xxxxx
```

### PropertyGraphIndex Import Error

```
Error: llama-index-graph-stores-neo4j not installed
```

Install the package:

```bash
pip install llama-index-graph-stores-neo4j
```

### Neo4j Connection Failed

The pipeline works without Neo4j. Entities and relations are extracted and returned, but not stored directly. Use the `to_graph_models()` method and store manually.

### Fallback Mode

If PropertyGraphIndex fails, the extractor automatically falls back to direct LLM extraction. Check logs for:

```
WARNING: Using fallback LLM extraction
```

## File Structure

```
services/rag_services/
├── app/core/extraction/
│   ├── hybrid_extractor.py      # Legacy (deprecated)
│   ├── llamaindex_extractor.py  # New LlamaIndex pipeline
│   └── schemas.py               # Shared schemas
│
├── tests/
│   └── test_llamaindex_extraction.py
│
└── docs/
    └── LLAMAINDEX_EXTRACTION.md  # This document
```

## Related Documentation

- [LlamaIndex RAG Integration](./LLAMAINDEX_INTEGRATION.md) - For search pipeline
- [Original Hybrid Extractor](../app/core/extraction/hybrid_extractor.py) - Legacy code
- [Graph Models](../core/domain/graph_models.py) - Output models
