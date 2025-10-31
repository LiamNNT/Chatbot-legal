"""
Pure domain service for context processing.

This service handles context processing without presentation concerns.
"""

from typing import List, Dict, Any
from ..core.domain import RAGContext


class ContextDomainService:
    """Pure domain service for context processing."""
    
    def extract_relevant_documents(self, rag_context: RAGContext, max_docs: int = 5) -> List[Dict[str, Any]]:
        """
        Extract most relevant documents from RAG context.
        
        Args:
            rag_context: RAG context containing retrieved documents
            max_docs: Maximum number of documents to extract
            
        Returns:
            List of relevant documents with metadata
        """
        relevant_docs = []
        
        for i, doc in enumerate(rag_context.retrieved_documents[:max_docs]):
            # RAG service returns 'text' field, fallback to 'content'
            content = doc.get("text", doc.get("content", "")).strip()
            
            if content and len(content) > 10:  # Filter out very short content
                relevant_docs.append({
                    "rank": i + 1,
                    "content": content,
                    "title": doc.get("title", f"Document {i + 1}"),
                    "metadata": doc.get("metadata", {}),
                    "relevance_score": rag_context.relevance_scores[i] if rag_context.relevance_scores and i < len(rag_context.relevance_scores) else 0.0
                })
        
        return relevant_docs
    
    def assess_context_quality(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assess the quality of retrieved context.
        
        Args:
            documents: List of relevant documents
            
        Returns:
            Quality assessment metrics
        """
        if not documents:
            return {
                "quality_score": 0.0,
                "has_sufficient_content": False,
                "average_relevance": 0.0,
                "document_count": 0
            }
        
        # RAG service returns 'text' field, fallback to 'content'
        total_content_length = sum(len(doc.get("text", doc.get("content", ""))) for doc in documents)
        average_relevance = sum(doc.get("relevance_score", 0.0) for doc in documents) / len(documents)
        
        quality_score = min(
            (average_relevance * 0.6) + 
            (min(total_content_length / 1000, 1.0) * 0.4), 
            1.0
        )
        
        return {
            "quality_score": quality_score,
            "has_sufficient_content": total_content_length > 100,
            "average_relevance": average_relevance,
            "document_count": len(documents),
            "total_content_length": total_content_length
        }