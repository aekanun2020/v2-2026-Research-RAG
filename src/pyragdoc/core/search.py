"""
Search orchestrator for coordinating multiple retrievers.

This module provides the SearchOrchestrator class that coordinates
BM25 and semantic search, applying RRF fusion for hybrid mode.
"""
import logging
from typing import List, Optional

from ..models.documents import SearchResult
from .bm25 import BM25Retriever
from .rrf import RRFCombiner
from ..utils.logging import get_logger


class SearchOrchestrator:
    """Coordinates search across multiple retrievers.
    
    The SearchOrchestrator routes search requests to appropriate retrievers
    based on the search mode:
    - "semantic": Use only semantic (vector) search via Qdrant
    - "bm25": Use only BM25 sparse retrieval
    - "hybrid": Use both and combine with RRF (default)
    
    It also implements graceful degradation: if one retriever fails,
    it falls back to the other.
    
    Attributes:
        bm25_retriever: BM25Retriever instance
        storage_service: QdrantService instance for semantic search
        embedding_service: EmbeddingService for generating query embeddings
        rrf_combiner: RRFCombiner for merging results
        default_mode: Default search mode (default: "hybrid")
        logger: Logger instance
    
    Example:
        >>> orchestrator = SearchOrchestrator(
        ...     bm25_retriever=bm25,
        ...     storage_service=qdrant,
        ...     embedding_service=embedder,
        ...     rrf_combiner=rrf
        ... )
        >>> results = await orchestrator.search("ข้อ ๒๑", limit=5, search_mode="hybrid")
    """
    
    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        storage_service,  # QdrantService (avoid circular import)
        embedding_service,  # EmbeddingService (avoid circular import)
        rrf_combiner: RRFCombiner,
        default_mode: str = "hybrid",
        logger: Optional[logging.Logger] = None
    ):
        """Initialize search orchestrator.
        
        Args:
            bm25_retriever: BM25Retriever instance
            storage_service: QdrantService instance for semantic search
            embedding_service: EmbeddingService for generating embeddings
            rrf_combiner: RRFCombiner for result fusion
            default_mode: Default search mode (default: "hybrid")
            logger: Optional logger instance
        """
        self.bm25_retriever = bm25_retriever
        self.storage_service = storage_service
        self.embedding_service = embedding_service
        self.rrf_combiner = rrf_combiner
        self.default_mode = default_mode
        self.logger = logger or get_logger(__name__)
        
        self.logger.info(
            f"SearchOrchestrator initialized with default_mode={default_mode}"
        )
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        search_mode: Optional[str] = None
    ) -> List[SearchResult]:
        """Execute search using specified mode.
        
        This is the main entry point for all search requests. It routes
        to the appropriate retriever(s) based on search_mode.
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            search_mode: One of "semantic", "bm25", "hybrid" (default: hybrid)
            
        Returns:
            List of SearchResult objects ranked by relevance
            
        Raises:
            ValueError: If search_mode is invalid
            RuntimeError: If all retrievers fail
        """
        mode = search_mode or self.default_mode
        
        # Ensure limit is an integer (handle string/float from external clients)
        limit = int(limit) if limit is not None else 5
        
        # Validate search mode
        valid_modes = ["semantic", "bm25", "hybrid"]
        if mode not in valid_modes:
            raise ValueError(
                f"Invalid search_mode: {mode}. Must be one of: {', '.join(valid_modes)}"
            )
        
        self.logger.info(f"Search request: query='{query}', limit={limit}, mode={mode}")
        
        # Route to appropriate search method
        if mode == "semantic":
            return await self._search_semantic(query, limit)
        elif mode == "bm25":
            return await self._search_bm25(query, limit)
        elif mode == "hybrid":
            return await self._search_hybrid(query, limit)
    
    async def _search_semantic(self, query: str, limit: int) -> List[SearchResult]:
        """Execute semantic-only search using Qdrant.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects from semantic search
        """
        self.logger.debug("Executing semantic-only search")
        
        # Generate embedding for query
        embedding = await self.embedding_service.generate_embedding(query)
        
        # Search in Qdrant
        results = await self.storage_service.search(embedding, limit)
        
        self.logger.info(f"Semantic search returned {len(results)} results")
        return results
    
    async def _search_bm25(self, query: str, limit: int) -> List[SearchResult]:
        """Execute BM25-only search.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects from BM25 search
        """
        self.logger.debug("Executing BM25-only search")
        
        # Search using BM25
        results = await self.bm25_retriever.search(query, limit)
        
        self.logger.info(f"BM25 search returned {len(results)} results")
        return results
    
    async def _search_hybrid(self, query: str, limit: int) -> List[SearchResult]:
        """Execute hybrid search with graceful degradation.
        
        This method:
        1. Executes BM25 and semantic searches in parallel
        2. Handles failures gracefully (falls back to working retriever)
        3. Combines results using RRF if both succeed
        
        Args:
            query: Search query text
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects combined with RRF
            
        Raises:
            RuntimeError: If both retrievers fail
        """
        self.logger.debug("Executing hybrid search")
        
        bm25_results = None
        semantic_results = None
        
        # Execute BM25 search with error handling
        try:
            bm25_results = await self.bm25_retriever.search(query, limit * 2)
            self.logger.debug(f"BM25 search succeeded: {len(bm25_results)} results")
        except Exception as e:
            self.logger.error(f"BM25 search failed: {e}", exc_info=True)
        
        # Execute semantic search with error handling
        try:
            embedding = await self.embedding_service.generate_embedding(query)
            semantic_results = await self.storage_service.search(embedding, limit * 2)
            self.logger.debug(f"Semantic search succeeded: {len(semantic_results)} results")
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}", exc_info=True)
        
        # Graceful degradation
        if bm25_results is None and semantic_results is None:
            error_msg = "All retrievers failed"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        elif bm25_results is None:
            self.logger.warning("BM25 failed, using semantic-only results")
            return semantic_results[:limit]
        elif semantic_results is None:
            self.logger.warning("Semantic failed, using BM25-only results")
            return bm25_results[:limit]
        
        # Both succeeded - combine using RRF
        self.logger.debug("Both retrievers succeeded, combining with RRF")
        combined_results = self.rrf_combiner.combine(
            [bm25_results, semantic_results],
            limit=limit
        )
        
        self.logger.info(
            f"Hybrid search returned {len(combined_results)} results "
            f"(BM25: {len(bm25_results)}, Semantic: {len(semantic_results)})"
        )
        
        return combined_results
    
    def get_stats(self) -> dict:
        """Get statistics about the search orchestrator.
        
        Returns:
            Dictionary with orchestrator statistics:
            - default_mode: Default search mode
            - bm25_stats: BM25 retriever statistics
            - rrf_stats: RRF combiner statistics
        """
        return {
            "default_mode": self.default_mode,
            "bm25_stats": self.bm25_retriever.get_index_stats(),
            "rrf_stats": self.rrf_combiner.get_stats()
        }
