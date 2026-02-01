# app/core/retrieval/neighbor_expander.py
"""
Neighbor Context Expander for Legal Document Chunks.

This module expands retrieved chunks with their neighbors (parent, siblings)
to provide better context for LLM response generation.

Key Features:
- Parent expansion: Include parent Điều when retrieving Khoản
- Sibling expansion: Include prev/next chunks for continuity
- Token-aware: Limits expansion to avoid context overflow
- Deduplication: Avoids adding chunks already in results
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Set

from app.core.retrieval.schemas import (
    NeighborContext,
    RetrievedChunk,
    Citation,
)

logger = logging.getLogger(__name__)


class NeighborExpander:
    """
    Expands retrieved chunks with neighbor context.
    
    Uses parent_id, prev_sibling_id, next_sibling_id from chunk metadata
    to fetch related chunks and provide richer context.
    
    Usage:
        expander = NeighborExpander(
            fetch_chunk_fn=vector_store.get_chunk_by_id,
            max_tokens=500,
        )
        
        expanded_chunks = await expander.expand(chunks)
    """
    
    def __init__(
        self,
        fetch_chunk_fn: Optional[Callable[[str], Any]] = None,
        fetch_chunks_fn: Optional[Callable[[List[str]], List[Any]]] = None,
        max_tokens_per_neighbor: int = 300,
        max_total_neighbor_tokens: int = 800,
        include_parent: bool = True,
        include_prev_sibling: bool = True,
        include_next_sibling: bool = True,
        token_estimator: Optional[Callable[[str], int]] = None,
    ):
        """
        Initialize the neighbor expander.
        
        Args:
            fetch_chunk_fn: Async function to fetch single chunk by ID
            fetch_chunks_fn: Async function to fetch multiple chunks by IDs
            max_tokens_per_neighbor: Max tokens per neighbor chunk
            max_total_neighbor_tokens: Max total tokens from all neighbors
            include_parent: Whether to include parent chunks
            include_prev_sibling: Whether to include previous sibling
            include_next_sibling: Whether to include next sibling
            token_estimator: Function to estimate tokens in text
        """
        self.fetch_chunk_fn = fetch_chunk_fn
        self.fetch_chunks_fn = fetch_chunks_fn
        self.max_tokens_per_neighbor = max_tokens_per_neighbor
        self.max_total_neighbor_tokens = max_total_neighbor_tokens
        self.include_parent = include_parent
        self.include_prev_sibling = include_prev_sibling
        self.include_next_sibling = include_next_sibling
        self.token_estimator = token_estimator or self._default_token_estimator
    
    @staticmethod
    def _default_token_estimator(text: str) -> int:
        """Simple token estimation: ~1.3 tokens per Vietnamese word."""
        if not text:
            return 0
        words = text.split()
        return int(len(words) * 1.3)
    
    async def expand(
        self,
        chunks: List[RetrievedChunk],
        existing_ids: Optional[Set[str]] = None,
    ) -> List[RetrievedChunk]:
        """
        Expand chunks with neighbor context.
        
        Args:
            chunks: List of retrieved chunks to expand
            existing_ids: Set of chunk IDs already in results (to avoid duplicates)
            
        Returns:
            List of chunks with neighbors populated
        """
        if not chunks:
            return chunks
        
        # Track existing chunk IDs to avoid duplicates
        if existing_ids is None:
            existing_ids = {chunk.chunk_id for chunk in chunks}
        
        # Collect all neighbor IDs to fetch
        neighbor_ids = self._collect_neighbor_ids(chunks, existing_ids)
        
        if not neighbor_ids:
            logger.debug("No neighbor IDs to fetch")
            return chunks
        
        # Fetch all neighbors in batch
        neighbors = await self._fetch_neighbors(list(neighbor_ids))
        
        # Build lookup map
        neighbor_map = {n.chunk_id: n for n in neighbors}
        
        # Populate neighbor context for each chunk
        for chunk in chunks:
            chunk.neighbors = self._build_neighbor_context(
                chunk, neighbor_map, existing_ids
            )
        
        logger.info(
            f"Expanded {len(chunks)} chunks with {len(neighbors)} neighbor chunks"
        )
        
        return chunks
    
    def _collect_neighbor_ids(
        self,
        chunks: List[RetrievedChunk],
        existing_ids: Set[str],
    ) -> Set[str]:
        """Collect all neighbor IDs that need to be fetched."""
        neighbor_ids: Set[str] = set()
        
        for chunk in chunks:
            if self.include_parent and chunk.parent_id:
                if chunk.parent_id not in existing_ids:
                    neighbor_ids.add(chunk.parent_id)
            
            if self.include_prev_sibling and chunk.prev_sibling_id:
                if chunk.prev_sibling_id not in existing_ids:
                    neighbor_ids.add(chunk.prev_sibling_id)
            
            if self.include_next_sibling and chunk.next_sibling_id:
                if chunk.next_sibling_id not in existing_ids:
                    neighbor_ids.add(chunk.next_sibling_id)
        
        return neighbor_ids
    
    async def _fetch_neighbors(
        self,
        neighbor_ids: List[str],
    ) -> List[RetrievedChunk]:
        """Fetch neighbor chunks by their IDs."""
        if not neighbor_ids:
            return []
        
        neighbors: List[RetrievedChunk] = []
        
        try:
            if self.fetch_chunks_fn:
                # Batch fetch
                raw_chunks = await self.fetch_chunks_fn(neighbor_ids)
                for raw in raw_chunks:
                    if raw:
                        neighbors.append(self._convert_to_retrieved_chunk(raw))
            
            elif self.fetch_chunk_fn:
                # Individual fetch (less efficient)
                for chunk_id in neighbor_ids:
                    try:
                        raw = await self.fetch_chunk_fn(chunk_id)
                        if raw:
                            neighbors.append(self._convert_to_retrieved_chunk(raw))
                    except Exception as e:
                        logger.warning(f"Failed to fetch neighbor {chunk_id}: {e}")
            
            else:
                logger.warning("No fetch function provided for neighbor expansion")
        
        except Exception as e:
            logger.error(f"Error fetching neighbors: {e}")
        
        return neighbors
    
    def _convert_to_retrieved_chunk(self, raw: Any) -> RetrievedChunk:
        """Convert raw chunk data to RetrievedChunk."""
        
        # Handle LlamaIndex TextNode
        if hasattr(raw, 'text') and hasattr(raw, 'metadata'):
            return RetrievedChunk.from_llama_node(raw, score=0.0)
        
        # Handle dict format
        if isinstance(raw, dict):
            chunk_id = raw.get("chunk_id", raw.get("id", str(id(raw))))
            metadata = raw.get("metadata", {})
            
            return RetrievedChunk(
                chunk_id=chunk_id,
                content=raw.get("content", raw.get("text", "")),
                embedding_prefix=raw.get("embedding_prefix"),
                score=0.0,
                metadata=metadata,
                citation=Citation.from_chunk_metadata(chunk_id, metadata),
                parent_id=metadata.get("parent_id"),
                prev_sibling_id=metadata.get("prev_sibling_id"),
                next_sibling_id=metadata.get("next_sibling_id"),
                retrieval_source="neighbor",
            )
        
        # Handle RetrievedChunk directly
        if isinstance(raw, RetrievedChunk):
            return raw
        
        # Fallback
        return RetrievedChunk(
            chunk_id=str(id(raw)),
            content=str(raw),
            score=0.0,
            retrieval_source="neighbor",
        )
    
    def _build_neighbor_context(
        self,
        chunk: RetrievedChunk,
        neighbor_map: Dict[str, RetrievedChunk],
        existing_ids: Set[str],
    ) -> NeighborContext:
        """Build NeighborContext for a chunk."""
        
        parent_chunk = None
        prev_sibling = None
        next_sibling = None
        
        total_tokens = 0
        
        # Get parent (highest priority)
        if self.include_parent and chunk.parent_id:
            parent = neighbor_map.get(chunk.parent_id)
            if parent:
                parent_tokens = self.token_estimator(parent.content)
                if parent_tokens <= self.max_tokens_per_neighbor:
                    parent_chunk = self._truncate_chunk(parent, self.max_tokens_per_neighbor)
                    total_tokens += parent_tokens
        
        # Get prev sibling
        if (
            self.include_prev_sibling
            and chunk.prev_sibling_id
            and total_tokens < self.max_total_neighbor_tokens
        ):
            prev = neighbor_map.get(chunk.prev_sibling_id)
            if prev:
                remaining_tokens = self.max_total_neighbor_tokens - total_tokens
                allowed_tokens = min(remaining_tokens, self.max_tokens_per_neighbor)
                prev_sibling = self._truncate_chunk(prev, allowed_tokens)
                total_tokens += self.token_estimator(prev_sibling.content)
        
        # Get next sibling
        if (
            self.include_next_sibling
            and chunk.next_sibling_id
            and total_tokens < self.max_total_neighbor_tokens
        ):
            next_chunk = neighbor_map.get(chunk.next_sibling_id)
            if next_chunk:
                remaining_tokens = self.max_total_neighbor_tokens - total_tokens
                allowed_tokens = min(remaining_tokens, self.max_tokens_per_neighbor)
                next_sibling = self._truncate_chunk(next_chunk, allowed_tokens)
        
        return NeighborContext(
            parent_chunk=parent_chunk,
            prev_sibling=prev_sibling,
            next_sibling=next_sibling,
        )
    
    def _truncate_chunk(
        self,
        chunk: RetrievedChunk,
        max_tokens: int,
    ) -> RetrievedChunk:
        """Truncate chunk content to fit within token limit."""
        
        current_tokens = self.token_estimator(chunk.content)
        
        if current_tokens <= max_tokens:
            return chunk
        
        # Truncate by words (approximate)
        words = chunk.content.split()
        target_words = int(max_tokens / 1.3)  # Reverse the estimation
        truncated_content = " ".join(words[:target_words]) + "..."
        
        # Create new chunk with truncated content
        return RetrievedChunk(
            chunk_id=chunk.chunk_id,
            content=truncated_content,
            embedding_prefix=chunk.embedding_prefix,
            score=chunk.score,
            metadata=chunk.metadata,
            citation=chunk.citation,
            parent_id=chunk.parent_id,
            prev_sibling_id=chunk.prev_sibling_id,
            next_sibling_id=chunk.next_sibling_id,
            retrieval_source=chunk.retrieval_source,
        )
    
    def get_all_expanded_chunks(
        self,
        chunks: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        """
        Get flat list of all chunks including neighbors.
        
        Args:
            chunks: List of chunks with populated neighbors
            
        Returns:
            Flat list with main chunks and their neighbors
        """
        all_chunks: List[RetrievedChunk] = []
        seen_ids: Set[str] = set()
        
        for chunk in chunks:
            if chunk.chunk_id not in seen_ids:
                all_chunks.append(chunk)
                seen_ids.add(chunk.chunk_id)
            
            if chunk.neighbors:
                for neighbor in chunk.neighbors.get_all_chunks():
                    if neighbor.chunk_id not in seen_ids:
                        all_chunks.append(neighbor)
                        seen_ids.add(neighbor.chunk_id)
        
        return all_chunks


def estimate_tokens_vietnamese(text: str) -> int:
    """
    Estimate tokens for Vietnamese text.
    
    Vietnamese uses spaces between syllables, and tokenizers typically
    produce ~1.3 tokens per syllable/word.
    
    Args:
        text: Vietnamese text
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    words = text.split()
    return int(len(words) * 1.3)
