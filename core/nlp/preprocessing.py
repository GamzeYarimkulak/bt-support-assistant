"""
Text preprocessing utilities for normalization and cleaning.
"""

import re
from typing import Optional, List
from langdetect import detect, LangDetectException
import structlog

logger = structlog.get_logger()


class TextPreprocessor:
    """
    Handles text preprocessing including:
    - Language detection
    - Normalization (lowercase, whitespace, etc.)
    - Tokenization
    - Basic cleaning
    """
    
    def __init__(self, lowercase: bool = True, remove_special_chars: bool = False):
        """
        Initialize text preprocessor.
        
        Args:
            lowercase: Whether to convert text to lowercase
            remove_special_chars: Whether to remove special characters
        """
        self.lowercase = lowercase
        self.remove_special_chars = remove_special_chars
        logger.info("text_preprocessor_initialized", 
                   lowercase=lowercase, 
                   remove_special_chars=remove_special_chars)
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of input text.
        
        Args:
            text: Input text
            
        Returns:
            ISO 639-1 language code (e.g., 'en', 'tr', 'de')
            Returns 'unknown' if detection fails
        """
        try:
            if not text or len(text.strip()) < 3:
                return "unknown"
            lang = detect(text)
            logger.debug("language_detected", language=lang)
            return lang
        except LangDetectException as e:
            logger.warning("language_detection_failed", error=str(e))
            return "unknown"
    
    def normalize(self, text: str) -> str:
        """
        Normalize text by cleaning whitespace and optionally lowercasing.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Lowercase if configured
        if self.lowercase:
            text = text.lower()
        
        # Remove special characters if configured
        if self.remove_special_chars:
            text = re.sub(r'[^\w\s]', '', text)
        
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """
        Simple whitespace tokenization.
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        if not text:
            return []
        
        normalized = self.normalize(text)
        tokens = normalized.split()
        return tokens
    
    def preprocess(self, text: str, detect_lang: bool = True) -> dict:
        """
        Full preprocessing pipeline.
        
        Args:
            text: Input text
            detect_lang: Whether to detect language
            
        Returns:
            Dictionary with preprocessed text, tokens, and language
        """
        if not text:
            return {
                "original": "",
                "normalized": "",
                "tokens": [],
                "language": "unknown"
            }
        
        language = self.detect_language(text) if detect_lang else "unknown"
        normalized = self.normalize(text)
        tokens = self.tokenize(text)
        
        return {
            "original": text,
            "normalized": normalized,
            "tokens": tokens,
            "language": language
        }
    
    def clean_query(self, query: str) -> str:
        """
        Clean user query for retrieval.
        Removes extra whitespace and normalizes, but preserves important punctuation.
        
        Args:
            query: User query
            
        Returns:
            Cleaned query
        """
        if not query:
            return ""
        
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query).strip()
        
        # Remove leading/trailing punctuation but preserve internal
        query = query.strip('.,;:!?')
        
        return query


