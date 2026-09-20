"""
Reciprocal Rank Fusion (RRF) for combining multiple rankings.

This module implements RRF, a scale-invariant algorithm for merging
ranked results from multiple retrievers (e.g., BM25 and semantic search).
"""
import logging
from typing import List, Dict, Optional
from collections import defaultdict

from ..models.documents import SearchResult
from ..utils.logging import get_logger


class RRFCombiner:
    """Reciprocal Rank Fusion for combining multiple rankings.
    
    RRF is a simple yet effective algorithm for combining rankings from
    multiple retrievers. It's scale-invariant, meaning it doesn't require
    tuning weights for different score ranges.
    
    The RRF score for a document is calculated as:
        RRF_score(d) = Σ (1 / (k + rank_i(d)))
    
    where:
    - d is a document
    - rank_i(d) is the rank of document d in retriever i (1-indexed)
    - k is a constant (typically 60)
    - The sum is over all retrievers where d appears
    
    Attributes:
        k: RRF constant (default: 60)
        logger: Logger instance for debugging
    
    Example:
        >>> combiner = RRFCombiner(k=60)
        >>> bm25_results = [...]  # Results from BM25
        >>> semantic_results = [...]  # Results from semantic search
        >>> combined = combiner.combine([bm25_results, semantic_results], limit=10)
    """
    
    def __init__(self, k: int = 60, logger: Optional[logging.Logger] = None):
        """Initialize RRF combiner.
        
        Args:
            k: RRF constant (default: 60, standard value from literature)
            logger: Optional logger instance
        """
        self.k = k
        self.logger = logger or get_logger(__name__)
        
        self.logger.info(f"RRFCombiner initialized with k={k}")
    
    def combine(
        self,
        result_lists: List[List[SearchResult]],
        limit: int
    ) -> List[SearchResult]:
        """Combine multiple ranked lists using RRF.
        
        This method:
        1. Calculates RRF scores for each document across all result lists
        2. Aggregates scores for documents appearing in multiple lists
        3. Sorts by descending RRF score
        4. Returns top-k results
        
        Args:
            result_lists: List of ranked SearchResult lists from different retrievers
            limit: Maximum number of results to return after fusion
            
        Returns:
            Combined and re-ranked list of SearchResult objects with RRF scores
            
        Raises:
            ValueError: If result_lists is empty or limit <= 0
            
        Example:
            >>> bm25_results = [
            ...     SearchResult(chunk=doc1, score=0.9),
            ...     SearchResult(chunk=doc2, score=0.7)
            ... ]
            >>> semantic_results = [
            ...     SearchResult(chunk=doc2, score=0.8),
            ...     SearchResult(chunk=doc3, score=0.6)
            ... ]
            >>> combined = combiner.combine([bm25_results, semantic_results], limit=5)
            >>> # doc2 appears in both lists, so gets higher RRF score
        """
        if not result_lists:
            raise ValueError("result_lists cannot be empty")
        
        if limit <= 0:
            raise ValueError(f"limit must be > 0, got {limit}")
        
        # Filter out empty result lists
        result_lists = [rl for rl in result_lists if rl]
        
        if not result_lists:
            self.logger.warning("All result lists are empty")
            return []
        
        self.logger.debug(
            f"Combining {len(result_lists)} result lists with RRF (k={self.k})"
        )
        
        # Calculate RRF scores for each document
        rrf_scores: Dict[str, float] = defaultdict(float)
        doc_map: Dict[str, SearchResult] = {}
        
        for result_list in result_lists:
            for rank, result in enumerate(result_list, start=1):
                # Use document ID or text as key for deduplication
                doc_key = self._get_document_key(result)
                
                # Calculate RRF score contribution from this ranking
                rrf_score = 1.0 / (self.k + rank)
                
                # Aggregate scores
                rrf_scores[doc_key] += rrf_score
                
                # Store document (keep first occurrence)
                if doc_key not in doc_map:
                    doc_map[doc_key] = result
        
        # Create combined results with RRF scores
        combined_results = []
        for doc_key, rrf_score in rrf_scores.items():
            result = doc_map[doc_key]
            combined_results.append(SearchResult(
                chunk=result.chunk,
                score=rrf_score
            ))
        
        # Sort by RRF score descending
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply limit
        combined_results = combined_results[:limit]
        
        self.logger.info(
            f"RRF combined {len(result_lists)} lists into {len(combined_results)} results"
        )
        
        return combined_results
    
    def _get_document_key(self, result: SearchResult) -> str:
        """Get a unique key for a document.
        
        Uses document ID if available, otherwise uses text content.
        This ensures documents are properly deduplicated across rankings.
        
        Args:
            result: SearchResult object
            
        Returns:
            Unique key string for the document
        """
        if result.chunk.id:
            return result.chunk.id
        else:
            # Fallback to text content (hash for efficiency)
            return str(hash(result.chunk.text))
    
    def get_stats(self) -> dict:
        """Get statistics about the RRF combiner.
        
        Returns:
            Dictionary with combiner statistics:
            - k: RRF constant value
        """
        return {
            "k": self.k
        }
