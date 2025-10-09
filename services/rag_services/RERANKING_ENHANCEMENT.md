# Cross-Encoder Reranking Enhancement

## Overview

This enhancement adds a sophisticated **Cross-Encoder Reranking layer** to the RAG services retrieval pipeline, significantly improving the accuracy of top search results. The reranker uses cross-encoder models to compute precise query-document relevance scores and reorder results for better quality.

## What is Cross-Encoder Reranking?

### Bi-Encoder vs Cross-Encoder

- **Bi-Encoder (Current Vector Search)**: Encodes query and documents separately, computes similarity via dot product/cosine similarity
- **Cross-Encoder (New Reranker)**: Processes query and document together through a single model, providing more accurate relevance scores

### Why Reranking Improves Accuracy

1. **Better Context Understanding**: Cross-encoders see the full query-document interaction
2. **Semantic Relevance**: More accurate relevance scoring than vector similarity alone
3. **Query-Specific Ranking**: Adapts ranking based on specific query intent
4. **Noise Reduction**: Filters out irrelevant results that may have high vector similarity

## Architecture Integration

The reranker integrates seamlessly into the existing Ports & Adapters architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Vector Search │    │  Keyword Search  │    │  Result Fusion  │
│   (Bi-Encoder) │ -> │     (BM25)       │ -> │     (RRF)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                              ┌─────────────────────────────────────┐
                              │     Cross-Encoder Reranker         │
                              │  • Query-document relevance        │
                              │  • Multilingual support (Vi/En)    │
                              │  • Batch processing optimization    │
                              │  • Detailed ranking metadata       │
                              └─────────────────────────────────────┘
                                                         │
                                                         ▼
                              ┌─────────────────────────────────────┐
                              │        Final Results                │
                              │   Ranked by Relevance Score        │
                              └─────────────────────────────────────┘
```

## Features

### ✅ **Advanced Cross-Encoder Models**
- Supports multiple cross-encoder architectures
- Default: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Optimized for Vietnamese content with multilingual models

### ✅ **Multilingual Support**
- Automatic language detection (Vietnamese vs English)
- Language-specific model routing
- Optimized for UIT chatbot domain

### ✅ **Performance Optimization**
- Batched processing for efficiency
- Asynchronous execution with thread pooling
- Configurable batch sizes and processing limits

### ✅ **Comprehensive Metadata**
- Original vs reranked positions
- Score transparency (vector, BM25, rerank)
- Processing time metrics
- Model information tracking

### ✅ **Graceful Fallback**
- No-op service when models unavailable
- Error handling with original result preservation
- Optional deployment (can be disabled)

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# Reranking Configuration
USE_RERANKING=true
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANK_BATCH_SIZE=16
RERANK_MAX_LENGTH=512
RERANK_TOP_K=20
VIETNAMESE_RERANK_MODEL=
```

### Settings.py Configuration

```python
# --- Reranking Configuration ---
use_reranking: bool = True  # Enable reranking with cross-encoder
rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Model name
rerank_batch_size: int = 16  # Batch size for processing
rerank_max_length: int = 512  # Maximum input length
rerank_top_k: int = 20  # Initial candidates for reranking
vietnamese_rerank_model: str = ""  # Optional Vietnamese-specific model
```

## Available Models

### General Purpose Models
- `cross-encoder/ms-marco-MiniLM-L-6-v2` - Fast, good performance
- `cross-encoder/ms-marco-MiniLM-L-12-v2` - Better accuracy, slower
- `cross-encoder/ms-marco-TinyBERT-L-2-v2` - Fastest, lower accuracy

### Multilingual Models
- `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` - Multilingual MARCO
- `sentence-transformers/msmarco-bert-base-dot-v5` - Good multilingual support

### Domain-Specific Models
You can fine-tune models on UIT-specific data for better performance.

## Usage Examples

### Basic Usage

```python
from adapters.cross_encoder_reranker import create_reranking_service
from core.domain.models import SearchResult

# Create reranking service
reranker = create_reranking_service(
    model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
    multilingual=True
)

# Rerank search results
query = "học phí đại học UIT"
reranked_results = await reranker.rerank(query, search_results, top_k=5)

# Check reranking metadata
for result in reranked_results:
    if result.reranking_metadata:
        print(f"Original rank: {result.reranking_metadata.original_rank}")
        print(f"New rank: {result.rank}")
        print(f"Rerank score: {result.reranking_metadata.rerank_score}")
```

### Custom Configuration

```python
# Vietnamese-optimized configuration
reranker = create_reranking_service(
    model_name="cross-encoder/ms-marco-MiniLM-L-12-v2",
    vietnamese_model_name="custom-vietnamese-cross-encoder",
    multilingual=True,
    batch_size=8,
    max_length=256
)
```

### Integration with Search Service

```python
from core.domain.search_service import SearchService
from core.domain.models import SearchQuery

# Create search query with reranking enabled
query = SearchQuery(
    text="hướng dẫn đăng ký học phần",
    top_k=10,
    use_rerank=True  # Enable reranking
)

# Execute search with automatic reranking
search_service = get_search_service()  # Includes reranker
response = await search_service.search(query)

# Results are automatically reranked
for result in response.results:
    print(f"Rank: {result.rank}, Score: {result.rerank_score}")
```

## Performance Considerations

### Memory Usage
- Cross-encoder models are memory-intensive
- Use appropriate batch sizes based on available RAM
- Consider model size vs accuracy tradeoffs

### Processing Time
- Reranking adds latency proportional to number of candidates
- Batch processing optimizes throughput
- Async execution prevents blocking

### Optimization Strategies

1. **Candidate Filtering**: Only rerank top N candidates (e.g., top 20)
2. **Batch Sizing**: Optimize batch size for your hardware
3. **Model Selection**: Balance accuracy vs speed requirements
4. **Caching**: Cache reranking results for repeated queries

## Monitoring and Metrics

### Available Metrics

```python
# Get reranking metadata
if result.reranking_metadata:
    metadata = result.reranking_metadata
    print(f"Processing time: {metadata.processing_time_ms}ms")
    print(f"Confidence: {metadata.confidence}")
    print(f"Model used: {metadata.model_name}")
```

### Performance Monitoring

```python
# Log reranking impact
original_top3 = [r.metadata.doc_id for r in original_results[:3]]
reranked_top3 = [r.metadata.doc_id for r in reranked_results[:3]]

if original_top3 != reranked_top3:
    logger.info(f"Reranking improved top-3: {original_top3} -> {reranked_top3}")
```

## Testing

### Run Unit Tests

```bash
cd services/rag_services
python -m pytest tests/test_cross_encoder_reranking.py -v
```

### Run Demo Script

```bash
cd services/rag_services
python scripts/demo_reranking.py
```

### Integration Testing

```python
# Test with real search pipeline
from core.container import get_search_service

search_service = get_search_service()
query = SearchQuery(text="học phí UIT", use_rerank=True)
response = await search_service.search(query)

# Verify reranking was applied
assert any(r.reranking_metadata is not None for r in response.results)
```

## Deployment

### Local Development

1. **Install Dependencies**:
   ```bash
   pip install sentence-transformers
   ```

2. **Configure Settings**:
   ```env
   USE_RERANKING=true
   RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
   ```

3. **Test Integration**:
   ```bash
   python scripts/demo_reranking.py
   ```

### Production Deployment

1. **Model Caching**: Pre-download models to avoid startup delays
2. **Resource Allocation**: Ensure sufficient RAM for model loading
3. **Monitoring**: Track reranking performance and impact
4. **Fallback Strategy**: Configure graceful degradation

### Docker Deployment

```dockerfile
# Add to Dockerfile
RUN pip install sentence-transformers

# Pre-download model (optional)
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

## Troubleshooting

### Common Issues

1. **Model Loading Fails**
   ```
   Error: sentence-transformers library not found
   ```
   **Solution**: Install sentence-transformers
   ```bash
   pip install sentence-transformers
   ```

2. **CUDA/GPU Issues**
   ```
   Error: CUDA out of memory
   ```
   **Solution**: Reduce batch size or use CPU
   ```python
   reranker = create_reranking_service(
       batch_size=4,  # Reduce batch size
       device="cpu"   # Force CPU usage
   )
   ```

3. **Slow Performance**
   ```
   Warning: Reranking takes too long
   ```
   **Solution**: Optimize configuration
   ```python
   # Use smaller, faster model
   reranker = create_reranking_service(
       model_name="cross-encoder/ms-marco-TinyBERT-L-2-v2",
       batch_size=32
   )
   ```

4. **Poor Results Quality**
   ```
   Issue: Reranking doesn't improve results
   ```
   **Solution**: Try different models or increase candidates
   ```python
   # Use better model with more candidates
   reranker = create_reranking_service(
       model_name="cross-encoder/ms-marco-MiniLM-L-12-v2"
   )
   
   # Increase candidate pool
   query.top_k = 50  # Get more initial candidates
   ```

## Benefits Achieved

### 🎯 **Improved Relevance**
- More accurate ranking based on query-document interaction
- Better understanding of semantic relevance
- Query-specific result ordering

### 🌐 **Multilingual Support** 
- Optimized for Vietnamese content
- Automatic language detection and routing
- Consistent performance across languages

### ⚡ **Performance Optimized**
- Batched processing for efficiency
- Asynchronous execution
- Configurable resource usage

### 📊 **Transparency**
- Detailed reranking metadata
- Score breakdown and explanations
- Performance metrics tracking

### 🛡️ **Robust Design**
- Graceful fallback when unavailable
- Error handling with original results
- Optional deployment flexibility

## Future Enhancements

### Planned Features
1. **Custom Model Training**: Fine-tune on UIT-specific data
2. **Adaptive Reranking**: Dynamic model selection based on query type
3. **Result Caching**: Cache reranking results for performance
4. **A/B Testing**: Compare reranking impact on user satisfaction

### Extensibility Points
1. **Custom Rerankers**: Implement domain-specific reranking logic
2. **Ensemble Methods**: Combine multiple reranking models
3. **Learning to Rank**: Implement more sophisticated ranking algorithms
4. **Real-time Fine-tuning**: Adapt models based on user feedback

---

## Summary

The Cross-Encoder Reranking enhancement provides:

✅ **Significantly improved search result accuracy**  
✅ **Multilingual support optimized for Vietnamese**  
✅ **Production-ready performance and scalability**  
✅ **Comprehensive monitoring and transparency**  
✅ **Seamless integration with existing architecture**  

Your RAG system now has state-of-the-art reranking capabilities that will provide users with more relevant and accurate search results! 🚀