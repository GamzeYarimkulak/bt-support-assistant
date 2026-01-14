"""
BT Support Assistant - FastAPI Uygulama Giriş Noktası

Bu modül, BT Support Assistant'ın ana FastAPI uygulamasını oluşturur ve yapılandırır.
API endpoint'lerini, middleware'leri ve static dosya servisini tanımlar.

Ana özellikler:
- RESTful API endpoint'leri (chat, health, anomaly)
- CORS desteği
- Web arayüzü servisi
- Structured logging
"""

from dotenv import load_dotenv

# .env dosyasını yükle (ayarları import etmeden ÖNCE yapılmalı)
# OpenAI API key gibi hassas bilgiler .env dosyasından okunur
# Encoding hatası durumunda sessizce atlanır (varsayılan değerler kullanılır)
try:
    load_dotenv(encoding='utf-8')
except:
    # Encoding hatası durumunda .env dosyası atlanır, varsayılan değerler kullanılır
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import structlog
from pathlib import Path

from app.config import settings
from app.routers import chat, health, anomaly

# Structured logging yapılandırması
# JSON formatında log çıktısı üretir (log aggregation sistemleri için uygun)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),  # ISO formatında zaman damgası
        structlog.processors.JSONRenderer()  # JSON formatında çıktı
    ]
)

logger = structlog.get_logger()

# FastAPI uygulamasını oluştur
# title, version, description gibi metadata bilgileri API dokümantasyonunda görünür
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Context-aware IT support assistant with hybrid RAG and anomaly detection",
    debug=settings.debug  # Debug modu: detaylı hata mesajları ve auto-reload
)

# CORS (Cross-Origin Resource Sharing) middleware
# Web arayüzünden API'ye istek göndermek için gerekli
# ÜRETİM ORTAMINDA: allow_origins=["*"] yerine spesifik domain'ler belirtilmeli
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tüm origin'lere izin ver (geliştirme için, üretimde değiştirilmeli)
    allow_credentials=True,  # Cookie ve authentication header'larına izin ver
    allow_methods=["*"],  # Tüm HTTP metodlarına izin ver (GET, POST, PUT, DELETE, vb.)
    allow_headers=["*"],  # Tüm header'lara izin ver
)

# Router'ları uygulamaya ekle
# Her router bir grup endpoint'i tanımlar (chat, health, anomaly)

# Health endpoint'i hem root hem de versioned path'te mevcut (kolaylık için)
app.include_router(health.router, tags=["health"])  # Root seviyesi: /health
app.include_router(health.router, prefix="/api/v1", tags=["health"])  # Versioned: /api/v1/health

# Chat endpoint'i: Kullanıcı sorularını yanıtlar
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])

# Anomali endpoint'i: Anomali tespiti ve istatistikleri
app.include_router(anomaly.router, prefix="/api/v1/anomaly", tags=["anomaly"])
# Endpoint'ler: /api/v1/anomaly/stats ve /api/v1/anomaly/detect

# ============================================
# Web Arayüzü (Frontend) Servisi
# ============================================
# Frontend klasörünü static dosya servisi olarak mount et
# HTML, CSS ve JavaScript dosyaları /ui/ path'i altında servis edilir
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    # /ui/ path'i altında frontend dosyalarını servis et
    app.mount("/ui", StaticFiles(directory=str(frontend_path)), name="frontend")
    logger.info("frontend_mounted", path=str(frontend_path))
    
    # Root path (/) Web UI'yi gösterir
    @app.get("/", include_in_schema=False)
    async def root():
        """
        Root path'te Web UI'yi servis eder.
        include_in_schema=False: Bu endpoint API dokümantasyonunda görünmez.
        """
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Frontend not found. Please check frontend/ directory."}
else:
    logger.warning("frontend_directory_not_found", path=str(frontend_path))


@app.on_event("startup")
async def startup_event():
    """
    Uygulama başlangıcında çalışan event handler.
    
    Bu fonksiyon uygulama başladığında bir kez çalışır.
    Model yükleme, indeks hazırlama gibi başlangıç işlemleri burada yapılabilir.
    """
    logger.info("application_startup", environment=settings.environment)
    # TODO: Modelleri, indeksleri vb. burada başlat


@app.on_event("shutdown")
async def shutdown_event():
    """
    Uygulama kapanışında çalışan event handler.
    
    Bu fonksiyon uygulama kapanırken bir kez çalışır.
    Açık bağlantıları kapatma, geçici dosyaları temizleme gibi işlemler yapılabilir.
    """
    logger.info("application_shutdown")
    # TODO: Kaynakları temizle (veritabanı bağlantıları, dosya handle'ları, vb.)


if __name__ == "__main__":
    """
    Script doğrudan çalıştırıldığında uvicorn sunucusunu başlatır.
    
    Bu mod, geliştirme için kullanışlıdır. Üretimde genellikle
    uvicorn komut satırından veya bir process manager (systemd, supervisor) ile çalıştırılır.
    """
    import uvicorn
    uvicorn.run(
        "app.main:app",  # Uygulama modülü ve instance'ı
        host=settings.api_host,  # Dinlenecek IP adresi (0.0.0.0 = tüm ağlar)
        port=settings.api_port,  # Dinlenecek port
        reload=settings.debug  # Debug modunda auto-reload aktif (kod değişikliklerinde otomatik yeniden başlatma)
    )


