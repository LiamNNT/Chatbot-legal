#!/usr/bin/env python3
# scripts/test_without_docker.py
#
# Test the Vietnamese Hybrid RAG system without Docker/OpenSearch
# Uses in-memory implementations for testing

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing Python imports...")
    
    try:
        # Test FastAPI
        import fastapi
        print(f"✅ FastAPI {fastapi.__version__}")
        
        # Test OpenSearch client
        import opensearchpy
        print(f"✅ OpenSearch-py {opensearchpy.__version__}")
        
        # Test sentence transformers
        import sentence_transformers
        print(f"✅ Sentence-transformers {sentence_transformers.__version__}")
        
        # Test FAISS
        import faiss
        print(f"✅ FAISS-CPU")
        
        # Test BM25
        import rank_bm25
        print(f"✅ Rank-BM25")
        
        # Test LlamaIndex
        import llama_index
        try:
            version = llama_index.__version__
        except AttributeError:
            version = "installed"
        print(f"✅ LlamaIndex {version}")
        
        print("\n✅ All critical dependencies are available!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_vietnamese_analyzer():
    """Test Vietnamese text processing."""
    print("\n🇻🇳 Testing Vietnamese text processing...")
    
    try:
        # Sample Vietnamese text
        vietnamese_texts = [
            "Trường Đại học Công nghệ Thông tin",
            "Quy định tuyển sinh năm 2024", 
            "Điều kiện tốt nghiệp đại học",
            "Chương trình đào tạo CNTT"
        ]
        
        # Test basic text processing
        processed_texts = []
        for text in vietnamese_texts:
            # Simple preprocessing (lowercasing, basic tokenization)
            processed = text.lower().replace("đại học", "university").replace("cntt", "công nghệ thông tin")
            processed_texts.append(processed)
            print(f"  '{text}' -> '{processed}'")
        
        print("✅ Vietnamese text processing test passed")
        return True
        
    except Exception as e:
        print(f"❌ Vietnamese processing error: {e}")
        return False

def test_embeddings():
    """Test sentence transformer embeddings."""
    print("\n🧠 Testing embeddings generation...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        # Use a lightweight model for testing
        model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        print(f"📥 Loading model: {model_name}")
        
        model = SentenceTransformer(model_name)
        
        # Test Vietnamese texts
        texts = [
            "tuyển sinh đại học",
            "điều kiện tốt nghiệp", 
            "chương trình đào tạo"
        ]
        
        print("🔢 Generating embeddings...")
        embeddings = model.encode(texts)
        
        print(f"✅ Generated embeddings: {embeddings.shape}")
        print(f"  📊 Embedding dimension: {embeddings.shape[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Embeddings error: {e}")
        return False

def test_bm25():
    """Test BM25 scoring."""
    print("\n🔍 Testing BM25 scoring...")
    
    try:
        from rank_bm25 import BM25Okapi
        
        # Sample Vietnamese documents
        documents = [
            "Quy định tuyển sinh đại học năm 2024 theo Bộ Giáo dục",
            "Điều kiện tốt nghiệp đại học công nghệ thông tin", 
            "Chương trình đào tạo ngành CNTT đại học",
            "Hướng dẫn sinh viên các quy định học tập"
        ]
        
        # Tokenize documents (simple word splitting for demo)
        tokenized_docs = [doc.lower().split() for doc in documents]
        
        # Create BM25 object
        bm25 = BM25Okapi(tokenized_docs)
        
        # Test query
        query = "tuyển sinh đại học"
        tokenized_query = query.lower().split()
        
        # Get BM25 scores
        scores = bm25.get_scores(tokenized_query)
        
        print(f"✅ BM25 scores for '{query}':")
        for i, (doc, score) in enumerate(zip(documents, scores)):
            print(f"  {i+1}. Score: {score:.3f} - {doc[:50]}...")
            
        return True
        
    except Exception as e:
        print(f"❌ BM25 error: {e}")
        return False

def test_faiss():
    """Test FAISS vector similarity."""
    print("\n⚡ Testing FAISS vector search...")
    
    try:
        import numpy as np
        import faiss
        
        # Create dummy embeddings (384 dimensions like multilingual model)
        dim = 384
        nb = 5  # number of vectors
        np.random.seed(42)
        
        # Sample vectors
        vectors = np.random.random((nb, dim)).astype('float32')
        
        # Create FAISS index
        index = faiss.IndexFlatL2(dim)
        index.add(vectors)
        
        print(f"✅ FAISS index created with {index.ntotal} vectors")
        
        # Test search
        query_vector = np.random.random((1, dim)).astype('float32')
        distances, indices = index.search(query_vector, k=3)
        
        print(f"✅ Top-3 search results:")
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            print(f"  {i+1}. Index: {idx}, Distance: {dist:.3f}")
            
        return True
        
    except Exception as e:
        print(f"❌ FAISS error: {e}")
        return False

def test_fusion_algorithm():
    """Test fusion algorithms.""" 
    print("\n🔬 Testing fusion algorithms...")
    
    try:
        # Mock BM25 and vector scores
        bm25_scores = [0.85, 0.72, 0.45, 0.33, 0.12]
        vector_scores = [0.92, 0.58, 0.67, 0.41, 0.23]
        
        # Reciprocal Rank Fusion (RRF)
        def reciprocal_rank_fusion(bm25_scores, vector_scores, k=60):
            # Sort indices by scores (descending)
            bm25_ranked = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
            vector_ranked = sorted(range(len(vector_scores)), key=lambda i: vector_scores[i], reverse=True)
            
            # Calculate RRF scores
            rrf_scores = [0] * len(bm25_scores)
            for i, idx in enumerate(bm25_ranked):
                rrf_scores[idx] += 1 / (k + i + 1)
            for i, idx in enumerate(vector_ranked):
                rrf_scores[idx] += 1 / (k + i + 1)
                
            return rrf_scores
        
        # Test RRF
        rrf_scores = reciprocal_rank_fusion(bm25_scores, vector_scores)
        
        print("✅ Reciprocal Rank Fusion results:")
        for i, (bm25, vector, rrf) in enumerate(zip(bm25_scores, vector_scores, rrf_scores)):
            print(f"  Doc {i}: BM25={bm25:.3f}, Vector={vector:.3f}, RRF={rrf:.4f}")
        
        # Test weighted fusion
        def weighted_fusion(bm25_scores, vector_scores, bm25_weight=0.6, vector_weight=0.4):
            return [bm25_weight * bm25 + vector_weight * vector 
                   for bm25, vector in zip(bm25_scores, vector_scores)]
        
        weighted_scores = weighted_fusion(bm25_scores, vector_scores)
        
        print("\n✅ Weighted fusion results:")
        for i, (bm25, vector, weighted) in enumerate(zip(bm25_scores, vector_scores, weighted_scores)):
            print(f"  Doc {i}: BM25={bm25:.3f}, Vector={vector:.3f}, Weighted={weighted:.3f}")
            
        return True
        
    except Exception as e:
        print(f"❌ Fusion error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Vietnamese Hybrid RAG System - Component Testing")
    print("=" * 60)
    print("📝 Testing without Docker/OpenSearch dependencies")
    print()
    
    tests = [
        test_imports,
        test_vietnamese_analyzer, 
        test_embeddings,
        test_bm25,
        test_faiss,
        test_fusion_algorithm
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"🧪 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All components working correctly!")
        print("\n🎯 Next steps:")
        print("  1. Install Docker to test full system")
        print("  2. Or run individual Python components")
        print("  3. Try: python app/main.py (FastAPI server)")
        return True
    else:
        print(f"❌ {total - passed} tests failed")
        print("🔧 Please check dependencies and fix errors")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
