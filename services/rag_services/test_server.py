#!/usr/bin/env python3
# test_server.py
# Simple FastAPI server for testing without all dependencies

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="Vietnamese Hybrid RAG System", 
    version="1.0.0",
    description="BM25 + Vector + Cross-Encoder system with Vietnamese language support"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    search_mode: str = "hybrid"
    size: int = 5
    language: str = "vi"
    faculty: Optional[str] = None
    doc_type: Optional[str] = None
    year: Optional[int] = None

class SearchResult(BaseModel):
    chunk_id: str
    title: str
    text: str
    score: float
    bm25_score: Optional[float] = None
    vector_score: Optional[float] = None

class SearchResponse(BaseModel):
    hits: List[SearchResult]
    total: int
    query: str
    search_mode: str

# Mock data for demo
mock_documents = [
    {
        "chunk_id": "doc1_chunk1",
        "title": "Quy chế tuyển sinh đại học năm 2024",
        "text": "Quy chế tuyển sinh đại học năm 2024 quy định các điều kiện, thủ tục và quy trình tuyển sinh vào các chương trình đào tạo đại học. Thí sinh cần đạt điểm chuẩn theo từng ngành và hoàn thành hồ sơ đăng ký theo quy định.",
        "faculty": "CNTT",
        "doc_type": "regulation",
        "year": 2024
    },
    {
        "chunk_id": "doc2_chunk1", 
        "title": "Chương trình đào tạo Công nghệ thông tin",
        "text": "Chương trình đào tạo ngành Công nghệ thông tin nhằm trang bị cho sinh viên các kiến thức cơ bản về lập trình, cơ sở dữ liệu, mạng máy tính và phát triển phần mềm.",
        "faculty": "CNTT",
        "doc_type": "syllabus", 
        "year": 2024
    },
    {
        "chunk_id": "doc3_chunk1",
        "title": "Điều kiện tốt nghiệp đại học",
        "text": "Để được công nhận tốt nghiệp, sinh viên phải hoàn thành đủ số tín chỉ theo chương trình đào tạo, đạt điểm trung bình tích lũy từ 2.0 trở lên và không có môn học nào bị điểm F.",
        "faculty": "CNTT",
        "doc_type": "regulation",
        "year": 2024
    }
]

@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "service": "Vietnamese Hybrid RAG System",
        "version": "1.0.0", 
        "description": "BM25 + Vector + Cross-Encoder with Vietnamese support",
        "features": [
            "🔍 BM25 keyword search",
            "🧠 Vector semantic search", 
            "⚡ Hybrid fusion (RRF + Weighted)",
            "🎯 Cross-encoder reranking",
            "🇻🇳 Vietnamese language support",
            "🏷️ Field filtering",
            "📍 Character span citation"
        ],
        "endpoints": [
            "/docs - API documentation",
            "/v1/health - Health check",
            "/v1/search - Hybrid search",
            "/v1/opensearch/* - OpenSearch management"
        ]
    }

@app.get("/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Vietnamese Hybrid RAG",
        "timestamp": "2025-09-29T00:00:00Z",
        "components": {
            "fastapi": "✅ Running",
            "opensearch": "⚠️ Not connected (demo mode)",
            "embeddings": "✅ Available", 
            "vietnamese_analyzer": "✅ Ready"
        }
    }

@app.post("/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Mock search endpoint for testing."""
    
    # Simple mock scoring based on query
    query_lower = request.query.lower()
    results = []
    
    for i, doc in enumerate(mock_documents):
        # Mock BM25 score
        bm25_score = 0.0
        if any(word in doc["text"].lower() for word in query_lower.split()):
            bm25_score = 0.8 - (i * 0.1)
            
        # Mock vector score  
        vector_score = 0.9 - (i * 0.15)
        
        # Mock hybrid score (weighted combination)
        hybrid_score = 0.6 * bm25_score + 0.4 * vector_score
        
        # Apply filters
        if request.faculty and doc["faculty"] != request.faculty:
            continue
        if request.doc_type and doc["doc_type"] != request.doc_type:
            continue
        if request.year and doc["year"] != request.year:
            continue
            
        results.append(SearchResult(
            chunk_id=doc["chunk_id"],
            title=doc["title"],
            text=doc["text"],
            score=hybrid_score,
            bm25_score=bm25_score,
            vector_score=vector_score
        ))
    
    # Sort by score
    results.sort(key=lambda x: x.score, reverse=True)
    
    # Limit results
    results = results[:request.size]
    
    return SearchResponse(
        hits=results,
        total=len(results),
        query=request.query,
        search_mode=request.search_mode
    )

@app.get("/v1/opensearch/health")
async def opensearch_health():
    """Mock OpenSearch health check."""
    return {
        "status": "red",
        "message": "OpenSearch not available in demo mode",
        "cluster_name": "vietnamese-rag-cluster",
        "index_exists": False,
        "demo_mode": True
    }

@app.get("/v1/opensearch/stats") 
async def opensearch_stats():
    """Mock OpenSearch statistics."""
    return {
        "total_documents": len(mock_documents),
        "index_name": "vietnamese-docs",
        "demo_mode": True,
        "vietnamese_analyzer": "ready",
        "field_mappings": {
            "text": "analyzed with vietnamese_analyzer",
            "faculty": "keyword",
            "doc_type": "keyword", 
            "year": "integer"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Vietnamese Hybrid RAG System (Demo Mode)")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/v1/health") 
    print("🔍 Demo Search: http://localhost:8000/v1/search")
    print()
    print("⚠️  Note: Running in demo mode without OpenSearch")
    print("   Install Docker and run 'make start' for full system")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
