"""
Application configuration management.
Loads settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "BT Support Assistant"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Model paths
    llm_model_name: str = "mistralai/Mistral-7B-Instruct-v0.2"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    models_dir: str = "./models"
    
    # Retrieval settings
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    top_k_retrieval: int = 10
    hybrid_alpha: float = 0.5  # Weight for combining BM25 and dense retrieval
    
    # RAG settings
    max_context_length: int = 2048
    confidence_threshold: float = 0.7
    temperature: float = 0.1
    
    # LLM settings (PHASE 8)
    use_real_llm: bool = False  # Toggle between stub and real LLM
    openai_api_key: Optional[str] = None
    llm_model: str = "gpt-4o-mini"  # gpt-4o-mini, gpt-4o, gpt-4-turbo
    llm_temperature: float = 0.3
    llm_max_tokens: int = 1500
    
    # Elasticsearch/OpenSearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index_tickets: str = "itsm_tickets"
    elasticsearch_index_docs: str = "internal_docs"
    
    # Vector store
    faiss_index_path: str = "./indexes/faiss_index.bin"
    vector_dim: int = 384
    
    # Anomaly detection
    anomaly_window_size: int = 100
    anomaly_threshold: float = 2.5
    drift_detection_window: int = 1000
    
    # Data pipeline
    data_dir: str = "./data"
    anonymization_enabled: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


# Global settings instance
settings = Settings()


