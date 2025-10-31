"""
RAG service adapter for integrating with the RAG services.

This adapter provides integration with the RAG system following the
Ports & Adapters architecture pattern.
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from ..ports.agent_ports import RAGServicePort


class RAGServiceAdapter(RAGServicePort):
    """
    Adapter for RAG service integration.
    
    This adapter implements the RAGServicePort interface to provide
    communication with the RAG services.
    """
    
    def __init__(
        self,
        rag_service_url: str = "http://localhost:8001",
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize the RAG service adapter.
        
        Args:
            rag_service_url: Base URL for the RAG service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.rag_service_url = rag_service_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"Content-Type": "application/json"}
            )
        return self._session
    
    async def retrieve_context(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Retrieve relevant context for a query using the RAG system.
        
        Args:
            query: The user query to search for relevant documents
            top_k: Number of top relevant documents to retrieve
            
        Returns:
            Dictionary containing retrieved documents and metadata
        """
        session = await self._get_session()
        
        payload = {
            "query": query,
            "top_k": top_k,
            "search_mode": "hybrid"  # Use hybrid search by default
        }
        
        for attempt in range(self.max_retries):
            try:
                async with session.post(
                    f"{self.rag_service_url}/v1/search",
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Transform response to standard format
                        # RAG service returns 'hits' not 'results'
                        hits = data.get("hits", [])
                        
                        return {
                            "query": query,
                            "retrieved_documents": hits,
                            "search_metadata": {
                                "total_results": data.get("total_hits", len(hits)),
                                "search_mode": data.get("search_mode", "hybrid"),
                                "processing_time": data.get("latency_ms"),
                                "top_k": top_k
                            },
                            "relevance_scores": [
                                doc.get("score", 0.0) 
                                for doc in hits
                            ]
                        }
                    
                    elif response.status == 503:  # Service unavailable
                        if attempt < self.max_retries - 1:
                            wait_time = 2 ** attempt
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise Exception(f"RAG service unavailable after {self.max_retries} attempts")
                    
                    else:
                        error_text = await response.text()
                        raise Exception(f"RAG service error {response.status}: {error_text}")
            
            except aiohttp.ClientError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Network error communicating with RAG service: {str(e)}")
        
        raise Exception("Max retries exceeded for RAG service")
    
    async def health_check(self) -> bool:
        """
        Check if the RAG service is healthy and available.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self.rag_service_url}/health"
            ) as response:
                return response.status == 200
        
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()