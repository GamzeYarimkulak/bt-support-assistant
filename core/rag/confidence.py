"""
Confidence estimation for RAG answers.
Implements heuristics to determine if the model has sufficient evidence.
"""

from typing import List, Dict, Any, Tuple
import re
import structlog

logger = structlog.get_logger()


class ConfidenceEstimator:
    """
    Estimates confidence in RAG-generated answers using multiple signals.
    """
    
    # Patterns indicating low confidence
    LOW_CONFIDENCE_PATTERNS = [
        r"i don'?t (have|know)",
        r"not enough information",
        r"cannot answer",
        r"unable to (answer|determine|find)",
        r"insufficient (information|data|context)",
        r"no (relevant|sufficient) (information|documents|context)",
    ]
    
    # Patterns indicating the model is making assumptions
    SPECULATION_PATTERNS = [
        r"might be",
        r"could be",
        r"perhaps",
        r"possibly",
        r"i think",
        r"i believe",
        r"probably",
    ]
    
    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize confidence estimator.
        
        Args:
            confidence_threshold: Minimum confidence for accepting an answer
        """
        self.confidence_threshold = confidence_threshold
        logger.info("confidence_estimator_initialized", threshold=confidence_threshold)
    
    def estimate_confidence(
        self,
        answer: str,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        retrieval_scores: List[float]
    ) -> Tuple[float, bool]:
        """
        Estimate confidence in the generated answer.
        
        Args:
            answer: Generated answer text
            query: Original user query
            retrieved_docs: Documents used for generation
            retrieval_scores: Relevance scores of retrieved documents
            
        Returns:
            Tuple of (confidence_score, has_answer)
        """
        if not answer or not retrieved_docs:
            return 0.0, False
        
        # Initialize confidence components
        confidence_signals = []
        
        # 1. Check for explicit refusal patterns
        has_refusal = self._has_low_confidence_patterns(answer)
        if has_refusal:
            logger.debug("low_confidence_pattern_detected", answer_snippet=answer[:100])
            return 0.0, False
        
        # 2. Check for speculation patterns
        has_speculation = self._has_speculation_patterns(answer)
        speculation_penalty = 0.3 if has_speculation else 0.0
        
        # 3. Retrieval quality score
        retrieval_quality = self._compute_retrieval_quality(retrieval_scores)
        confidence_signals.append(retrieval_quality)
        
        # 4. Answer-context overlap
        context_overlap = self._compute_context_overlap(answer, retrieved_docs)
        confidence_signals.append(context_overlap)
        
        # 5. Answer length heuristic (very short answers might be uncertain)
        length_score = self._compute_length_score(answer)
        confidence_signals.append(length_score)
        
        # Aggregate confidence
        base_confidence = sum(confidence_signals) / len(confidence_signals)
        final_confidence = max(0.0, base_confidence - speculation_penalty)
        
        has_answer = final_confidence >= self.confidence_threshold
        
        logger.debug("confidence_estimated",
                    confidence=final_confidence,
                    has_answer=has_answer,
                    retrieval_quality=retrieval_quality,
                    context_overlap=context_overlap)
        
        return final_confidence, has_answer
    
    def _has_low_confidence_patterns(self, text: str) -> bool:
        """
        Check if text contains patterns indicating low confidence or refusal.
        
        Args:
            text: Text to check
            
        Returns:
            True if low confidence patterns found
        """
        text_lower = text.lower()
        for pattern in self.LOW_CONFIDENCE_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def _has_speculation_patterns(self, text: str) -> bool:
        """
        Check if text contains speculative language.
        
        Args:
            text: Text to check
            
        Returns:
            True if speculation patterns found
        """
        text_lower = text.lower()
        for pattern in self.SPECULATION_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def _compute_retrieval_quality(self, scores: List[float]) -> float:
        """
        Compute quality score from retrieval scores.
        
        Args:
            scores: List of retrieval scores
            
        Returns:
            Quality score [0, 1]
        """
        if not scores:
            return 0.0
        
        # Use top score and average of top-3
        top_score = max(scores)
        top_3_avg = sum(sorted(scores, reverse=True)[:3]) / min(3, len(scores))
        
        # Weighted combination
        quality = 0.6 * top_score + 0.4 * top_3_avg
        
        return min(1.0, quality)
    
    def _compute_context_overlap(self, answer: str, documents: List[Dict[str, Any]]) -> float:
        """
        Compute overlap between answer and context documents.
        
        Args:
            answer: Generated answer
            documents: Context documents
            
        Returns:
            Overlap score [0, 1]
        """
        if not answer or not documents:
            return 0.0
        
        # Extract answer tokens
        answer_tokens = set(answer.lower().split())
        
        # Remove very common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "are"}
        answer_tokens = answer_tokens - stop_words
        
        if not answer_tokens:
            return 0.5  # Neutral score for very short answers
        
        # Compute overlap with documents
        context_tokens = set()
        for doc in documents:
            text = doc.get("text", "")
            context_tokens.update(text.lower().split())
        
        context_tokens = context_tokens - stop_words
        
        if not context_tokens:
            return 0.0
        
        # Jaccard similarity
        intersection = len(answer_tokens & context_tokens)
        union = len(answer_tokens | context_tokens)
        
        overlap = intersection / union if union > 0 else 0.0
        
        return overlap
    
    def _compute_length_score(self, answer: str) -> float:
        """
        Compute score based on answer length.
        Too short might indicate uncertainty, but we don't penalize concise answers too much.
        
        Args:
            answer: Generated answer
            
        Returns:
            Length score [0, 1]
        """
        if not answer:
            return 0.0
        
        word_count = len(answer.split())
        
        # Score based on word count
        if word_count < 5:
            return 0.3
        elif word_count < 10:
            return 0.6
        elif word_count < 20:
            return 0.9
        else:
            return 1.0


