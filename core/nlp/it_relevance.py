"""
IT relevance checker - Filters out non-IT related queries.
"""

import re
from typing import Tuple
import structlog

logger = structlog.get_logger()

# IT-related keywords (Turkish and English)
IT_KEYWORDS = [
    # Hardware
    'bilgisayar', 'laptop', 'yazıcı', 'printer', 'monitör', 'klavye', 'mouse', 'fare',
    'donanım', 'hardware', 'disk', 'ram', 'bellek', 'ekran',
    
    # Software/Applications
    'yazılım', 'software', 'program', 'uygulama', 'app', 'outlook', 'excel', 'word',
    'teams', 'office', 'windows', 'linux', 'macos', 'sistem', 'system',
    
    # Network/Internet
    'ağ', 'network', 'internet', 'wifi', 'wi-fi', 'vpn', 'bağlantı', 'connection',
    'ip', 'dns', 'sunucu', 'server', 'email', 'e-posta', 'mail',
    
    # Security/Authentication
    'şifre', 'password', 'güvenlik', 'security', 'kimlik', 'authentication', 'login',
    'giriş', 'mfa', '2fa', 'çok faktörlü', 'multi-factor',
    
    # IT Support Terms
    'hata', 'error', 'sorun', 'problem', 'bug', 'çözüm', 'solution', 'destek', 'support',
    'ticket', 'kayıt', 'troubleshoot', 'giderme', 'sıfırlama', 'reset',
    
    # Technical Terms
    'sürücü', 'driver', 'güncelleme', 'update', 'yükleme', 'install', 'kurulum',
    'ayar', 'setting', 'yapılandırma', 'configuration', 'backup', 'yedekleme',
]

# Non-IT keywords that should be rejected
NON_IT_KEYWORDS = [
    'şişe', 'bottle', 'kapak', 'lid', 'açmak', 'open bottle',
    'yemek', 'food', 'içecek', 'drink', 'su', 'water',
    'ev', 'home', 'araba', 'car', 'yol', 'road',
    'sağlık', 'health', 'ilaç', 'medicine', 'doktor', 'doctor',
]


class ITRelevanceChecker:
    """
    Checks if a query is IT-related or not.
    """
    
    def __init__(self):
        """Initialize IT relevance checker."""
        # Compile regex patterns for faster matching
        # Use word boundaries but also allow Turkish suffixes (şişeyi, şişeyle, etc.)
        self.it_patterns = [re.compile(re.escape(kw.lower()), re.IGNORECASE) 
                           for kw in IT_KEYWORDS]
        self.non_it_patterns = [re.compile(re.escape(kw.lower()), re.IGNORECASE) 
                               for kw in NON_IT_KEYWORDS]
        
        logger.info("it_relevance_checker_initialized",
                   it_keywords_count=len(IT_KEYWORDS),
                   non_it_keywords_count=len(NON_IT_KEYWORDS))
    
    def is_it_related(self, query: str) -> Tuple[bool, float]:
        """
        Check if query is IT-related.
        
        Args:
            query: User query text
            
        Returns:
            Tuple of (is_it_related: bool, confidence: float)
            confidence is between 0.0 and 1.0
        """
        if not query or len(query.strip()) < 3:
            return False, 0.0
        
        query_lower = query.lower()
        
        # First check for explicit non-IT keywords (high priority)
        for pattern in self.non_it_patterns:
            if pattern.search(query_lower):
                logger.debug("non_it_query_detected", query=query[:50])
                return False, 0.9  # High confidence it's not IT-related
        
        # Count IT keyword matches
        it_matches = sum(1 for pattern in self.it_patterns if pattern.search(query_lower))
        
        # Calculate confidence based on matches
        if it_matches == 0:
            # No IT keywords found - likely not IT-related
            return False, 0.7
        elif it_matches >= 2:
            # Multiple IT keywords - definitely IT-related
            return True, 0.9
        else:
            # Single IT keyword - probably IT-related but lower confidence
            return True, 0.6
    
    def should_reject_query(self, query: str) -> bool:
        """
        Determine if query should be rejected as non-IT.
        
        Args:
            query: User query text
            
        Returns:
            True if query should be rejected, False otherwise
        """
        is_it, confidence = self.is_it_related(query)
        
        # Reject if not IT-related with high confidence
        if not is_it and confidence >= 0.7:
            logger.info("query_rejected_non_it", 
                       query=query[:50],
                       confidence=confidence)
            return True
        
        return False

