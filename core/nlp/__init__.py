"""
NLP module for text preprocessing and intent classification.
"""

from core.nlp.preprocessing import TextPreprocessor
from core.nlp.intent import IntentClassifier
from core.nlp.it_relevance import ITRelevanceChecker

__all__ = ["TextPreprocessor", "IntentClassifier", "ITRelevanceChecker"]


