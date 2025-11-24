# HƯỚNG DẪN: CẤU HÌNH VÀ CHẠY LLM EXTRACTION VỚI OPENROUTER

## Tổng quan

Hệ thống **đã có đầy đủ khả năng** extract entities và relations từ văn bản tiếng Việt để xây dựng Knowledge Graph. Đã hoàn thành:

✅ **LLM Extraction System**
- `LLMRelationExtractor` - Trích xuất quan hệ giữa entities
- `CategoryGuidedEntityExtractor` - Trích xuất entities theo category
- `GraphETLPipeline` - Pipeline từ documents → graph
- OpenRouter client - Hỗ trợ nhiều LLM providers

✅ **Neo4j Integration**
- Neo4j adapter hoạt động tốt
- Graph repository với đầy đủ CRUD operations
- Container đang chạy: `neo4j-catrag` tại ports 7474, 7687

✅ **Scripts sẵn sàng**
- `demo_openrouter_extraction.py` - Demo extraction với OpenRouter
- `build_graph_from_indexed_data.py` - Build graph từ data đã index
- `test_graph_status.py` - Kiểm tra trạng thái hệ thống

---

## Cấu hình OpenRouter

### 1. Lấy API Key

Truy cập: https://openrouter.ai/keys

Tạo API key mới (miễn phí có $1 credit để test)

### 2. Cập nhật file `.env`

File: `/home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services/.env`

```bash
# LLM Configuration
LLM_PROVIDER=openrouter
LLM_MODEL=google/gemini-flash-1.5  # Rẻ, nhanh, tốt cho tiếng Việt
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=2000

# OpenRouter (sử dụng OpenAI-compatible API)
OPENAI_API_KEY=sk-or-v1-YOUR_KEY_HERE  # ← Điền API key của bạn vào đây
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=uitchatbot
```

### 3. Models được đề xuất

**Giá rẻ & nhanh (cho development):**
```bash
LLM_MODEL=google/gemini-flash-1.5      # $0.000075/1K input tokens
LLM_MODEL=meta-llama/llama-3.1-8b-instruct  # Free!
```

**Chất lượng cao (cho production):**
```bash
LLM_MODEL=anthropic/claude-3.5-sonnet  # $3/1M input tokens
LLM_MODEL=google/gemini-pro-1.5        # $0.00125/1K input tokens
LLM_MODEL=openai/gpt-4-turbo           # Qua OpenRouter
```

Xem thêm: https://openrouter.ai/models

---

## Cách chạy Extraction

### Option 1: Demo extraction với sample text

```bash
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services

# Chạy demo
python scripts/demo_openrouter_extraction.py
```

Script này sẽ:
1. ✅ Extract entities từ sample text (về quy định học tập)
2. 🤖 Call OpenRouter LLM để extract relations
3. 📊 Build sample graph nodes trong Neo4j
4. 📄 Hiển thị kết quả chi tiết

### Option 2: Build graph từ documents đã index

```bash
# Nếu đã index documents trước đó
python scripts/build_graph_from_indexed_data.py
```

### Option 3: Kiểm tra trạng thái hệ thống

```bash
python scripts/test_graph_status.py
```

---

## Xem Graph trên Neo4j Browser

### 1. Mở Neo4j Browser

URL: http://localhost:7474

Login:
- Username: `neo4j`
- Password: `uitchatbot`

### 2. Queries để khám phá graph

**Xem tất cả nodes:**
```cypher
MATCH (n) 
RETURN n 
LIMIT 50
```

**Xem quan hệ:**
```cypher
MATCH p=()-[r]->() 
RETURN p 
LIMIT 25
```

**Xem nodes theo category:**
```cypher
MATCH (n:MON_HOC) 
RETURN n.name, n.code, n.credits
```

**Tìm prerequisite relationships:**
```cypher
MATCH (source:MON_HOC)-[r:TIEN_QUYET]->(target:MON_HOC)
RETURN source.name, target.name, r.confidence
ORDER BY r.confidence DESC
```

**Graph visualization với path:**
```cypher
MATCH path = (a)-[*1..3]-(b)
WHERE a.name CONTAINS 'IT003'
RETURN path
LIMIT 10
```

---

## Cấu trúc LLM Extractor

### File quan trọng

```
services/rag_services/
├── adapters/llm/
│   ├── openrouter_client.py      # ✨ OpenRouter client (MỚI)
│   ├── openai_client.py           # OpenAI/Gemini clients
│   ├── llm_client.py              # Base LLM interface
│   └── __init__.py
│
├── indexing/
│   ├── llm_relation_extractor.py          # LLM-based relation extraction
│   ├── category_guided_entity_extractor.py # Entity extraction
│   └── graph_etl_pipeline.py              # ETL pipeline
│
├── scripts/
│   ├── demo_openrouter_extraction.py  # ✨ Demo script (MỚI)
│   ├── test_graph_status.py          # ✨ Status checker (MỚI)
│   └── build_graph_from_indexed_data.py
│
└── .env  # ← CẤU HÌNH Ở ĐÂY
```

### Cách sử dụng trong code

```python
from adapters.llm import create_llm_client_from_env
from indexing.llm_relation_extractor import LLMRelationExtractor
from indexing.category_guided_entity_extractor import CategoryGuidedEntityExtractor

# 1. Extract entities
entity_extractor = CategoryGuidedEntityExtractor()
entities_dict = entity_extractor.extract(text)
entities = [e for ents in entities_dict.values() for e in ents]

# 2. Initialize LLM client
llm_client = create_llm_client_from_env()  # Đọc từ .env

# 3. Extract relations
relation_extractor = LLMRelationExtractor(llm_client)
result = await relation_extractor.extract_relations(
    text=text,
    entities=entities,
    use_few_shot=True
)

print(f"Extracted {len(result.relations)} relations")
print(f"Cost: ${result.cost_usd:.4f}")
```

---

## Troubleshooting

### Lỗi: "OPENAI_API_KEY not set"

**Nguyên nhân:** Chưa cấu hình API key trong `.env`

**Giải pháp:**
```bash
# Edit .env file
OPENAI_API_KEY=sk-or-v1-YOUR_ACTUAL_KEY
```

### Lỗi: "Neo4j connection failed"

**Nguyên nhân:** Neo4j container không chạy hoặc password sai

**Giải pháp:**
```bash
# Check container
docker ps | grep neo4j

# Start if not running
docker-compose -f docker/docker-compose.neo4j.yml up -d

# Check password in .env matches Neo4j
NEO4J_PASSWORD=uitchatbot
```

### LLM timeout

**Nguyên nhân:** Model chậm hoặc network issue

**Giải pháp:**
- Đổi sang model nhanh hơn: `google/gemini-flash-1.5`
- Giảm `LLM_MAX_TOKENS`
- Check OpenRouter status: https://status.openrouter.ai

### Cost quá cao

**Giải pháp:**
```bash
# Dùng model miễn phí
LLM_MODEL=meta-llama/llama-3.1-8b-instruct

# Hoặc Gemini Flash (rất rẻ)
LLM_MODEL=google/gemini-flash-1.5  # $0.075/1M tokens
```

---

## Next Steps

### 1. Test extraction ngay
```bash
python scripts/demo_openrouter_extraction.py
```

### 2. Index real data
```bash
python scripts/index_quy_dinh_v2.py data/quy_dinh
```

### 3. Build full graph
```bash
python scripts/build_graph_from_indexed_data.py
```

### 4. Integrate với Router Agent
Sử dụng extracted graph để enhance RAG responses

---

## Summary

🎉 **Hệ thống đã sẵn sàng!**

✅ LLM extraction code hoàn chỉnh
✅ OpenRouter integration
✅ Neo4j đang chạy
✅ Scripts demo sẵn sàng

📝 **Chỉ cần:**
1. Thêm OpenRouter API key vào `.env`
2. Chạy `demo_openrouter_extraction.py`
3. Xem kết quả trên Neo4j Browser (localhost:7474)

🔗 **Resources:**
- OpenRouter: https://openrouter.ai
- Neo4j Browser: http://localhost:7474
- Models: https://openrouter.ai/models
- Docs: https://openrouter.ai/docs
