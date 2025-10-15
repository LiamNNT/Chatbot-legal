# 🚀 Weaviate Migration - Quick Start

## Tổng Quan Nhanh

Hệ thống RAG đã được migrate từ **FAISS/Chroma + LlamaIndex** sang **Weaviate** - vector database hiện đại, gọn nhẹ và production-ready.

## ⚡ Quick Start (< 5 phút)

### 1. Cài Đặt Dependencies

```bash
cd services/rag_services
pip install -r requirements.txt
```

### 2. Start Hệ Thống

**Cách 1: Script tự động (Khuyên dùng)**
```bash
chmod +x scripts/start_weaviate_system.sh
./scripts/start_weaviate_system.sh
```

**Cách 2: Manual**
```bash
# Start Docker services
cd docker
docker-compose up -d

# Start RAG API
cd ..
python start_server.py
```

### 3. Verify

```bash
# Check Weaviate
curl http://localhost:8080/v1/.well-known/ready

# Check API
curl http://localhost:8000/v1/health
```

## 📦 Những Gì Đã Thay Đổi

### ✅ Lợi Ích

1. **Code đơn giản hơn** - Bỏ LlamaIndex abstraction layer
2. **Ít dependencies hơn** - Từ 10+ packages xuống còn 2
3. **Hiệu suất cao hơn** - HNSW indexing native
4. **Production-ready** - Scaling, backup, monitoring built-in

### 📝 Files Mới

- `store/vector/weaviate_store.py` - Weaviate client & schema
- `adapters/weaviate_vector_adapter.py` - Vector search adapter
- `docker/docker-compose.weaviate.yml` - Weaviate Docker config
- `scripts/migrate_to_weaviate.py` - Migration utility
- `scripts/start_weaviate_system.sh` - Quick start script
- `WEAVIATE_MIGRATION.md` - Chi tiết đầy đủ
- `WEAVIATE_MIGRATION_SUMMARY.md` - Tổng hợp

### 🔄 Files Deprecated

- `store/vector/faiss_store.py` ❌
- `store/vector/chroma_store.py` ❌
- `adapters/llamaindex_vector_adapter.py` ❌

### ⚙️ Configuration Mới

`.env`:
```bash
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=                    # Empty for local dev
EMB_MODEL=intfloat/multilingual-e5-base
```

## 💻 Usage Example

### Index Documents

```python
from infrastructure.container import get_container
from core.domain.models import DocumentChunk, DocumentMetadata

# Get service
container = get_container()
vector_repo = container.get_vector_repository()

# Create chunks
chunks = [
    DocumentChunk(
        text="Quy định về điều kiện tốt nghiệp...",
        metadata=DocumentMetadata(
            doc_id="reg_2024_001",
            title="Quy chế đào tạo 2024",
            faculty="CNTT",
            year=2024,
            doc_type="regulation"
        ),
        chunk_index=0
    )
]

# Index
await vector_repo.index_documents(chunks)
```

### Search Documents

```python
from core.domain.models import SearchQuery, SearchMode, SearchFilters

# Simple search
query = SearchQuery(
    text="điều kiện tốt nghiệp",
    top_k=10,
    search_mode=SearchMode.VECTOR
)

results = await vector_repo.search(query)

# With filters
query = SearchQuery(
    text="học phí",
    top_k=5,
    filters=SearchFilters(
        faculties=["CNTT"],
        years=[2024],
        doc_types=["regulation"]
    )
)

results = await vector_repo.search(query)
```

## 🐛 Troubleshooting

### Weaviate không start được?

```bash
# Check logs
docker logs vietnamese-rag-weaviate

# Restart
docker-compose -f docker/docker-compose.yml restart weaviate
```

### Import errors?

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Cần reset data?

```python
from store.vector.weaviate_store import (
    get_weaviate_client, 
    delete_document_collection, 
    create_document_collection
)

client = get_weaviate_client()
delete_document_collection(client)  # Xóa collection
create_document_collection(client)   # Tạo lại
```

## 📚 Documentation

- **Chi tiết đầy đủ**: `WEAVIATE_MIGRATION.md`
- **Tổng hợp**: `WEAVIATE_MIGRATION_SUMMARY.md`
- **Weaviate Docs**: https://weaviate.io/developers/weaviate

## 🎯 Next Steps

1. ✅ Cài dependencies
2. ✅ Start services
3. ✅ Index documents của bạn
4. ✅ Test search
5. 🚀 Deploy to production!

## 💡 Key Commands

```bash
# Start everything
./scripts/start_weaviate_system.sh

# Stop services
cd docker && docker-compose down

# View logs
docker logs vietnamese-rag-weaviate
docker logs vietnamese-rag-opensearch

# Check collection
curl http://localhost:8080/v1/schema/VietnameseDocument | jq

# Migrate from old storage (if needed)
python scripts/migrate_to_weaviate.py --source ./storage
```

## ✅ Checklist

- [ ] Đọc `WEAVIATE_MIGRATION.md`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Start services: `./scripts/start_weaviate_system.sh`
- [ ] Verify health: `curl http://localhost:8080/v1/.well-known/ready`
- [ ] Index test documents
- [ ] Run search tests
- [ ] Check performance

---

**Hệ thống đã sẵn sàng! 🎉**

Weaviate giúp hệ thống:
- ✅ Gọn nhẹ hơn
- ✅ Hiệu quả hơn  
- ✅ Dễ maintain hơn
- ✅ Sẵn sàng scale

Có câu hỏi? Xem `WEAVIATE_MIGRATION.md` hoặc Weaviate docs!
