"""
Intent classification for user queries.
Categorizes queries into predefined intents for better routing.
"""

from typing import Optional, Dict, List
from enum import Enum
import re
import structlog

logger = structlog.get_logger()


class QueryIntent(str, Enum):
    """Predefined query intents."""
    HOW_TO = "how_to"  # How to do something
    TROUBLESHOOT = "troubleshoot"  # Problem solving
    WHAT_IS = "what_is"  # Definition/explanation
    STATUS = "status"  # Status check
    ACCESS = "access"  # Access/permission requests
    OTHER = "other"  # Catch-all


class IntentClassifier:
    """
    Simple rule-based intent classifier.
    Can be extended with ML-based classification later.
    """
    
    def __init__(self):
        """Initialize intent classifier with keyword patterns."""
        self.intent_patterns = {
            QueryIntent.HOW_TO: [
                r'\bhow\s+(to|do|can)\b',
                r'\bsteps\s+to\b',
                r'\bway\s+to\b',
            ],
            QueryIntent.TROUBLESHOOT: [
                r'\b(not\s+work(ing)?|doesn\'t\s+work|broken|error|issue|problem|fail(ing|ed)?)\b',
                r'\bcan\'t\b',
                r'\bunable\s+to\b',
                r'\bfix\b',
            ],
            QueryIntent.WHAT_IS: [
                r'\bwhat\s+(is|are)\b',
                r'\bdefin(e|ition)\b',
                r'\bexplain\b',
                r'\bmean(s|ing)\b',
            ],
            QueryIntent.STATUS: [
                r'\bstatus\s+of\b',
                r'\bwhen\s+will\b',
                r'\bhow\s+long\b',
                r'\bprogress\b',
            ],
            QueryIntent.ACCESS: [
                r'\b(access|permission|grant|request)\b',
                r'\bcan\s+i\s+(access|use|get)\b',
                r'\bneed\s+(access|permission)\b',
            ],
        }
        
        logger.info("intent_classifier_initialized")
    
    def classify(self, query: str) -> QueryIntent:
        """
        Classify query intent using pattern matching.
        
        Args:
            query: User query text
            
        Returns:
            Detected intent
        """
        if not query:
            return QueryIntent.OTHER
        
        query_lower = query.lower()
        
        # Check each intent's patterns
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    logger.debug("intent_detected", intent=intent.value, query=query)
                    return intent
        
        logger.debug("intent_default", intent=QueryIntent.OTHER.value, query=query)
        return QueryIntent.OTHER
    
    def classify_with_confidence(self, query: str) -> Dict[str, float]:
        """
        Classify query with confidence scores for all intents.
        
        Args:
            query: User query text
            
        Returns:
            Dictionary mapping intent to confidence score
        """
        if not query:
            return {intent.value: 0.0 for intent in QueryIntent}
        
        query_lower = query.lower()
        scores = {intent.value: 0.0 for intent in QueryIntent}
        
        # Count pattern matches for each intent
        for intent, patterns in self.intent_patterns.items():
            matches = sum(1 for pattern in patterns if re.search(pattern, query_lower))
            if matches > 0:
                # Simple scoring: normalize by number of patterns
                scores[intent.value] = min(matches / len(patterns), 1.0)
        
        # If no matches, set OTHER to 1.0
        if all(score == 0.0 for score in scores.values()):
            scores[QueryIntent.OTHER.value] = 1.0
        
        return scores
    
    def get_intent_description(self, intent: QueryIntent) -> str:
        """
        Get human-readable description of an intent.
        
        Args:
            intent: Query intent
            
        Returns:
            Intent description
        """
        descriptions = {
            QueryIntent.HOW_TO: "Instructions or procedures",
            QueryIntent.TROUBLESHOOT: "Problem solving or error resolution",
            QueryIntent.WHAT_IS: "Definitions or explanations",
            QueryIntent.STATUS: "Status checks or progress inquiries",
            QueryIntent.ACCESS: "Access or permission requests",
            QueryIntent.OTHER: "General query",
        }
        return descriptions.get(intent, "Unknown intent")


