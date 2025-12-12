"""
Hybrid retrieval combining BM25 and embedding-based search.
"""

from typing import List, Dict, Any
import numpy as np
import structlog

from core.retrieval.bm25_retriever import BM25Retriever
from core.retrieval.embedding_retriever import EmbeddingRetriever
from core.retrieval.dynamic_weighting import DynamicWeightComputer

logger = structlog.get_logger()


class HybridRetriever:
    """
    Combines BM25 (lexical) and embedding-based (semantic) retrieval
    using weighted score fusion.
    """
    
    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        embedding_retriever: EmbeddingRetriever,
        alpha: float = 0.5,
        use_dynamic_weighting: bool = True
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            bm25_retriever: BM25 retriever instance
            embedding_retriever: Embedding retriever instance
            alpha: Default weight for BM25 scores (1-alpha for embedding scores)
                  alpha=1.0 means BM25 only, alpha=0.0 means embeddings only
                  Only used if use_dynamic_weighting=False
            use_dynamic_weighting: If True, compute alpha dynamically based on query
        """
        self.bm25_retriever = bm25_retriever
        self.embedding_retriever = embedding_retriever
        self.alpha = alpha  # Default/fallback alpha
        self.use_dynamic_weighting = use_dynamic_weighting
        
        # Initialize dynamic weight computer if enabled
        if use_dynamic_weighting:
            self.weight_computer = DynamicWeightComputer()
        else:
            self.weight_computer = None
        
        logger.info("hybrid_retriever_initialized", 
                   alpha=alpha,
                   use_dynamic_weighting=use_dynamic_weighting)
    
    def search(
        self, 
        query: str, 
        top_k: int = 10,
        bm25_k: int = 50,
        embedding_k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining BM25 and embedding retrieval.
        
        Args:
            query: Search query
            top_k: Number of final results to return
            bm25_k: Number of candidates from BM25
            embedding_k: Number of candidates from embeddings
            
        Returns:
            List of retrieved documents with hybrid scores
            
        Process:
            1. Retrieve top-k candidates from BM25
            2. Retrieve top-k candidates from embeddings
            3. Normalize scores independently
            4. Combine scores using weighted sum
            5. Re-rank and return top-k
        """
        # Compute dynamic alpha if enabled
        if self.use_dynamic_weighting and self.weight_computer:
            query_alpha = self.weight_computer.compute_alpha(query)
            logger.debug("dynamic_alpha_computed",
                        query=query[:50],
                        computed_alpha=query_alpha,
                        default_alpha=self.alpha)
        else:
            query_alpha = self.alpha
        
        # Retrieve from both methods
        bm25_results = self.bm25_retriever.search(query, top_k=bm25_k)
        embedding_results = self.embedding_retriever.search(query, top_k=embedding_k)
        
        # Create score dictionaries
        bm25_scores = {
            self._get_doc_id(doc): doc["score"] 
            for doc in bm25_results
        }
        embedding_scores = {
            self._get_doc_id(doc): doc["score"] 
            for doc in embedding_results
        }
        
        # Normalize scores
        bm25_scores_norm = self._normalize_scores(bm25_scores)
        embedding_scores_norm = self._normalize_scores(embedding_scores)
        
        # Combine all unique documents
        all_docs = {}
        for doc in bm25_results + embedding_results:
            doc_id = self._get_doc_id(doc)
            if doc_id not in all_docs:
                all_docs[doc_id] = doc
        
        # Compute hybrid scores
        hybrid_results = []
        for doc_id, doc in all_docs.items():
            bm25_score = bm25_scores_norm.get(doc_id, 0.0)
            embedding_score = embedding_scores_norm.get(doc_id, 0.0)
            
            # Weighted combination (use query-specific alpha if dynamic weighting is enabled)
            current_alpha = query_alpha if self.use_dynamic_weighting else self.alpha
            hybrid_score = current_alpha * bm25_score + (1 - current_alpha) * embedding_score
            
            result = doc.copy()
            result["score"] = hybrid_score
            result["bm25_score"] = bm25_score
            result["embedding_score"] = embedding_score
            result["retrieval_method"] = "hybrid"
            result["alpha_used"] = current_alpha if self.use_dynamic_weighting else self.alpha
            
            hybrid_results.append(result)
        
        # Sort by hybrid score and return top-k
        hybrid_results.sort(key=lambda x: x["score"], reverse=True)
        final_results = hybrid_results[:top_k]
        
        logger.debug("hybrid_search_completed",
                    query=query,
                    num_bm25=len(bm25_results),
                    num_embedding=len(embedding_results),
                    num_hybrid=len(final_results),
                    alpha_used=query_alpha if self.use_dynamic_weighting else self.alpha)
        
        # Add metadata about source counts for debug info
        for result in final_results:
            result["_bm25_source_count"] = len(bm25_results)
            result["_embedding_source_count"] = len(embedding_results)
        
        return final_results
    
    def _get_doc_id(self, doc: Dict[str, Any]) -> str:
        """
        Get unique document identifier.
        
        Args:
            doc: Document dictionary
            
        Returns:
            Document ID
        """
        # Try common ID fields
        for id_field in ["id", "doc_id", "ticket_id", "_id"]:
            if id_field in doc:
                return str(doc[id_field])
        
        # Fallback to text hash
        return str(hash(doc.get("text", "")))
    
    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize scores to [0, 1] range using min-max normalization.
        
        Args:
            scores: Dictionary mapping doc_id to score
            
        Returns:
            Dictionary with normalized scores
        """
        if not scores:
            return {}
        
        score_values = np.array(list(scores.values()))
        
        # Min-max normalization
        min_score = score_values.min()
        max_score = score_values.max()
        
        if max_score - min_score < 1e-6:  # Avoid division by zero
            return {doc_id: 1.0 for doc_id in scores}
        
        normalized = {
            doc_id: float((score - min_score) / (max_score - min_score))
            for doc_id, score in scores.items()
        }
        
        return normalized
    
    def set_alpha(self, alpha: float):
        """
        Update the alpha weight for score combination.
        
        Args:
            alpha: New alpha value (0.0 to 1.0)
        """
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("Alpha must be between 0.0 and 1.0")
        
        self.alpha = alpha
        logger.info("alpha_updated", alpha=alpha)


