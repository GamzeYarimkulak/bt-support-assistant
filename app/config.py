"""
Uygulama Yapılandırma Yönetimi

Bu modül, uygulamanın tüm ayarlarını yönetir. Ayarlar şu sırayla yüklenir:
1. Ortam değişkenleri (.env dosyası veya sistem environment variables)
2. Varsayılan değerler (aşağıda tanımlanan default değerler)

Pydantic Settings kullanarak tip güvenliği ve doğrulama sağlanır.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """
    Uygulama ayarları sınıfı.
    
    Tüm ayarlar ortam değişkenlerinden yüklenir. Eğer bir değişken
    tanımlı değilse, aşağıdaki varsayılan değerler kullanılır.
    
    Kullanım:
        from app.config import settings
        print(settings.api_port)  # 8000 (varsayılan) veya .env'den gelen değer
    """
    
    # ============================================
    # Uygulama Genel Ayarları
    # ============================================
    app_name: str = "BT Support Assistant"  # Uygulama adı (API dokümantasyonunda görünür)
    app_version: str = "0.1.0"  # Uygulama versiyonu
    environment: str = "development"  # Ortam: development, staging, production
    debug: bool = True  # Debug modu: detaylı hata mesajları ve auto-reload
    
    # ============================================
    # API Sunucu Ayarları
    # ============================================
    api_host: str = "0.0.0.0"  # Dinlenecek IP (0.0.0.0 = tüm ağ arayüzleri)
    api_port: int = 8000  # Dinlenecek port numarası
    
    # ============================================
    # Model Ayarları
    # ============================================
    llm_model_name: str = "mistralai/Mistral-7B-Instruct-v0.2"  # LLM model adı (şu an kullanılmıyor, OpenAI kullanılıyor)
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"  # Embedding modeli (384 boyutlu vektörler)
    models_dir: str = "./models"  # Modellerin saklanacağı klasör
    
    # ============================================
    # Arama (Retrieval) Ayarları
    # ============================================
    bm25_k1: float = 1.5  # BM25 k1 parametresi (terim frekansı ağırlığı)
    bm25_b: float = 0.75  # BM25 b parametresi (doküman uzunluğu normalizasyonu)
    top_k_retrieval: int = 10  # Her arama yönteminden alınacak maksimum sonuç sayısı
    hybrid_alpha: float = 0.5  # Hibrit arama için varsayılan alpha değeri (dinamik ağırlıklandırma kapalıysa kullanılır)
    
    # ============================================
    # KB (Knowledge Base) Boost Ayarları
    # ============================================
    kb_boost_enabled: bool = True  # KB dokümanlarını arama sonuçlarında önceliklendir
    kb_boost_factor: float = 1.15  # KB dokümanları için boost faktörü (1.15 = %15 artış)
    
    # ============================================
    # RAG (Retrieval-Augmented Generation) Ayarları
    # ============================================
    max_context_length: int = 2048  # LLM'e gönderilecek maksimum context uzunluğu (token sayısı)
    confidence_threshold: float = 0.7  # Minimum güven skoru eşiği (altında cevap verilmez)
    temperature: float = 0.1  # LLM temperature (düşük = daha deterministik, yüksek = daha yaratıcı)
    
    # ============================================
    # LLM (Large Language Model) Ayarları
    # ============================================
    use_real_llm: bool = False  # Gerçek LLM kullan (True) veya stub kullan (False)
    openai_api_key: Optional[str] = None  # OpenAI API anahtarı (.env dosyasından yüklenir)
    llm_model: str = "gpt-4o-mini"  # Kullanılacak OpenAI modeli (gpt-4o-mini, gpt-4o, gpt-4-turbo)
    llm_temperature: float = 0.3  # LLM temperature (0.0-1.0 arası, düşük = daha tutarlı)
    llm_max_tokens: int = 1500  # LLM yanıtı için maksimum token sayısı
    
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
    
    # ============================================
    # Chat Loglama Ayarları
    # ============================================
    save_chat_logs: bool = True  # Kullanıcı sorguları ve yanıtları dosyaya kaydet
    chat_logs_dir: str = "./data/processed/chat_logs"  # Chat log dosyalarının saklanacağı klasör
    save_as_tickets: bool = True  # Sorguları ticket formatında da kaydet (anomali tespiti için)
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    class Config:
        """
        Pydantic Settings yapılandırması.
        """
        env_file = ".env"  # Ortam değişkenlerinin yükleneceği dosya
        # Pydantic birden fazla encoding'i desteklemez, bu yüzden manuel olarak handle ediyoruz
        env_file_encoding = "utf-8"  # Varsayılan encoding (dosya UTF-8 değilse hata verebilir)
        case_sensitive = False  # Ortam değişkeni isimleri büyük/küçük harf duyarsız
        extra = "ignore"  # .env dosyasındaki ekstra alanları yoksay (hata verme)


# Global ayarlar instance'ı
# Basit başlatma - .env dosyasında encoding sorunu olsa bile varsayılan değerler kullanılır
settings = Settings()


