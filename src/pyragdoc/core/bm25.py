"""
BM25-based sparse retrieval with Thai tokenization.

This module provides BM25 (Best Matching 25) retrieval for exact term matching,
particularly useful for Thai section numbers and specific terminology.
"""
import logging
from typing import List, Optional

from rank_bm25 import BM25Okapi

from ..models.documents import DocumentChunk, SearchResult
from ..utils.thai_tokenizer import ThaiTokenizer
from ..utils.logging import get_logger


class BM25Retriever:
    """BM25-based sparse retrieval with Thai tokenization.
    
    This retriever uses the BM25 algorithm for ranking documents based on
    term frequency and inverse document frequency. It's particularly effective
    for exact term matching, such as Thai section numbers (e.g., "ข้อ ๒๑").
    
    The retriever uses Thai-aware tokenization to properly handle Thai text,
    preserving section numbers, abbreviations, and numerals as single tokens.
    
    Attributes:
        tokenizer: ThaiTokenizer instance for text processing
        k1: Term frequency saturation parameter (default: 1.5)
        b: Length normalization parameter (default: 0.75)
        index: BM25Okapi index (built from documents)
        documents: List of indexed DocumentChunk objects
    """
    
    def __init__(
        self,
        tokenizer: ThaiTokenizer,
        k1: float = 1.5,
        b: float = 0.75,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize BM25 retriever.
        
        Args:
            tokenizer: ThaiTokenizer instance for text processing
            k1: Term frequency saturation parameter (default: 1.5)
                Higher values give more weight to term frequency
            b: Length normalization parameter (default: 0.75)
                0 = no normalization, 1 = full normalization
            logger: Optional logger instance
        """
        self.tokenizer = tokenizer
        self.k1 = k1
        self.b = b
        self.logger = logger or get_logger(__name__)
        self.index: Optional[BM25Okapi] = None
        self.documents: List[DocumentChunk] = []
        
        self.logger.info(
            f"BM25Retriever initialized with k1={k1}, b={b}"
        )
    
    async def index_documents(self, documents: List[DocumentChunk]) -> None:
        """Build BM25 index from documents.
        
        This method tokenizes all documents and builds a BM25 index for
        efficient retrieval. The index is stored in memory.
        
        Args:
            documents: List of DocumentChunk objects to index
            
        Raises:
            ValueError: If documents list is empty
        """
        if not documents:
            raise ValueError("Cannot index empty document list")
        
        self.logger.info(f"Indexing {len(documents)} documents for BM25 search")
        
        # Store documents
        self.documents = documents
        
        # Tokenize all documents
        tokenized_docs = []
        for i, doc in enumerate(documents):
            tokens = self.tokenizer.tokenize(doc.text)
            tokenized_docs.append(tokens)
            
            if i % 100 == 0 and i > 0:
                self.logger.debug(f"Tokenized {i}/{len(documents)} documents")
        
        # Build BM25 index
        self.index = BM25Okapi(tokenized_docs, k1=self.k1, b=self.b)
        
        self.logger.info(
            f"Successfully indexed {len(documents)} documents for BM25 search"
        )
    
    async def add_documents(self, documents: List[DocumentChunk]) -> None:
        """Add documents to existing index (incremental indexing).
        
        Note: rank-bm25 doesn't support true incremental updates, so this
        method rebuilds the entire index with the new documents added.
        
        Args:
            documents: List of DocumentChunk objects to add
            
        Raises:
            ValueError: If documents list is empty
        """
        if not documents:
            raise ValueError("Cannot add empty document list")
        
        self.logger.info(f"Adding {len(documents)} documents to BM25 index")
        
        # Add to existing documents
        self.documents.extend(documents)
        
        # Rebuild index (rank-bm25 doesn't support incremental updates)
        await self.index_documents(self.documents)
        
        self.logger.info(
            f"Successfully added {len(documents)} documents. "
            f"Total documents: {len(self.documents)}"
        )
    
    async def search(self, query: str, limit: int) -> List[SearchResult]:
        """Search using BM25 algorithm.
        
        This method tokenizes the query, calculates BM25 scores for all
        documents, and returns the top-k results sorted by score.
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            
        Returns:
            List of SearchResult objects with BM25 scores, sorted by
            score descending
            
        Raises:
            RuntimeError: If index not built (call index_documents first)
            ValueError: If query is empty or limit <= 0
        """
        if self.index is None:
            raise RuntimeError(
                "BM25 index not built. Call index_documents() first."
            )
        
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if limit <= 0:
            raise ValueError(f"Limit must be > 0, got {limit}")
        
        # Tokenize query
        query_tokens = self.tokenizer.tokenize(query)
        self.logger.debug(
            f"Query tokenized into {len(query_tokens)} tokens: {query_tokens}"
        )
        
        if not query_tokens:
            self.logger.warning("Query tokenization resulted in no tokens")
            return []
        
        # Get BM25 scores for all documents
        scores = self.index.get_scores(query_tokens)
        
        # Create results with normalized scores
        results = []
        max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0
        
        for idx, score in enumerate(scores):
            if score > 0:  # Only include documents with non-zero scores
                normalized_score = float(score / max_score)
                results.append(SearchResult(
                    chunk=self.documents[idx],
                    score=normalized_score
                ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply limit
        results = results[:limit]
        
        self.logger.info(
            f"BM25 search returned {len(results)} results "
            f"(max_score={max_score:.4f})"
        )
        
        return results
    
    def get_index_stats(self) -> dict:
        """Get statistics about the BM25 index.
        
        Returns:
            Dictionary with index statistics:
            - num_documents: Number of indexed documents
            - has_index: Whether index is built
            - k1: Term frequency saturation parameter
            - b: Length normalization parameter
        """
        return {
            "num_documents": len(self.documents),
            "has_index": self.index is not None,
            "k1": self.k1,
            "b": self.b
        }
