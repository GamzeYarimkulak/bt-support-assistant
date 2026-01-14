# BT Support Assistant

Kurumsal BT yardım masaları için geliştirilmiş, hibrit arama teknolojisi ve anomali tespiti özelliklerine sahip bir yapay zeka destekli destek asistanı. Sistem, ITSM ticket'ları ve iç dokümanlar üzerinden güvenilir yanıtlar üretir ve zaman içindeki içerik değişimlerini izleyerek proaktif uyarılar sağlar.

## Özellikler

### Hibrit Arama Sistemi
- **BM25 (Kelime Bazlı Arama)**: Klasik bilgi erişim yöntemi ile tam eşleşme ve anahtar kelime araması
- **Embedding (Anlam Bazlı Arama)**: Semantik benzerlik ile kavramsal eşleştirme
- **Dinamik Ağırlıklandırma**: Sorgu tipine göre otomatik olarak BM25 ve embedding ağırlıklarını ayarlar
  - Kısa teknik sorgular → Embedding ağırlıklı (alpha ~0.2-0.4)
  - Orta uzunlukta sorgular → Dengeli (alpha ~0.5)
  - Uzun detaylı sorgular → BM25 ağırlıklı (alpha ~0.6-0.8)

### Güvenilirlik ve Kalite Kontrolü
- **"Kaynak Yoksa Cevap Yok" İlkesi**: Güvenilir kaynak bulunamazsa sistem cevap vermez
- **Güven Skoru**: Her yanıt için 0.0-1.0 arası güvenilirlik skoru hesaplanır
- **Eşik Değeri Kontrolü**: Minimum güven skoru altındaki yanıtlar reddedilir

### Anomali Tespiti
- Yeni konu gruplarını tespit eder
- İçerik kaymalarını (drift) izler
- Olağandışı ticket desenlerini erken uyarı olarak bildirir

### Veri Güvenliği ve Uyumluluk
- **KVKK Uyumu**: PII (Kişisel Tanımlanabilir Bilgi) anonimleştirme
- Email, telefon, IP adresi ve isim gibi hassas bilgiler otomatik olarak anonimleştirilir

### Dil Desteği
- Türkçe ve İngilizce sorgular desteklenir
- Türkçe-İngilizce karışık teknik terimler anlaşılır
- Otomatik dil tespiti yapılır

### Akıllı Filtreleme
- BT ile ilgili olmayan sorular otomatik olarak reddedilir
- IT relevance checker ile sorgu analizi yapılır
- Konuşma geçmişi bağlamında takip soruları desteklenir

### Konuşma Yönetimi
- Session bazlı konuşma geçmişi saklanır
- Önceki mesajlara referans vererek bağlamsal yanıtlar üretilir
- Son 10 mesaj (5 kullanıcı + 5 asistan) otomatik olarak hatırlanır

## Kurulum

### Gereksinimler
- Python 3.8 veya üzeri
- Conda (önerilen) veya pip
- 8GB+ RAM (model yükleme için)
- Windows/Linux/macOS

### Adım 1: Ortam Hazırlama

Conda kullanıyorsanız:

```bash
conda create -n bt-support python=3.10
conda activate bt-support
```

Virtual environment kullanıyorsanız:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### Adım 2: Bağımlılıkları Yükleme

```bash
pip install -r requirements.txt
```

**Not**: Windows kullanıcıları için PyTorch kurulumu ayrıca gerekebilir. Detaylar için [PyTorch resmi sitesini](https://pytorch.org/) ziyaret edin.

### Adım 3: Ortam Değişkenlerini Ayarlama

Proje kök dizininde `.env` dosyası oluşturun:

```env
# OpenAI API (opsiyonel - gerçek LLM kullanmak için)
USE_REAL_LLM=false
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini

# Uygulama Ayarları
APP_NAME=BT Support Assistant
ENVIRONMENT=development
DEBUG=true

# API Ayarları
API_HOST=0.0.0.0
API_PORT=8000

# Model Ayarları
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

### Adım 4: Veri Hazırlama

Veri dosyalarınızı aşağıdaki yapıya göre yerleştirin:

```
data/
├── raw/
│   ├── tickets/          # ITSM ticket CSV dosyaları
│   └── kb/              # PDF dokümanlar
└── processed/           # İşlenmiş veriler (otomatik oluşturulur)
```

### Adım 5: İndeksleri Oluşturma

```bash
python scripts/build_and_test_index.py
```

Bu komut:
- Ticket'ları işler ve anonimleştirir
- PDF dokümanları parçalara ayırır
- BM25 indeksini oluşturur
- Embedding vektörlerini hesaplar ve FAISS indeksini oluşturur
- İndeksleri `indexes/` klasörüne kaydeder

### Adım 6: Sunucuyu Başlatma

```bash
python scripts/run_server.py
```

Sunucu başladıktan sonra:
- Web arayüzü: http://localhost:8000
- API dokümantasyonu: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## Kullanım

### Web Arayüzü

1. Tarayıcınızda `http://localhost:8000` adresini açın
2. Chat sekmesinde sorunuzu yazın
3. Sistem yanıtı, kaynakları ve güven skorunu gösterir
4. Debug sekmesinde arama detaylarını inceleyebilirsiniz

### API Kullanımı

#### Chat Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Outlook şifremi unuttum, nasıl sıfırlarım?",
    "language": "tr",
    "session_id": "user-123"
  }'
```

Yanıt formatı:

```json
{
  "answer": "Outlook şifre sıfırlama işlemi için...",
  "confidence": 0.85,
  "has_answer": true,
  "sources": [
    {
      "doc_id": "TCK-001",
      "doc_type": "ticket",
      "title": "Outlook şifre sıfırlama",
      "snippet": "...",
      "relevance_score": 0.92
    }
  ],
  "language": "tr",
  "timestamp": "2025-01-17T10:30:00",
  "debug_info": {
    "alpha_used": 0.35,
    "query_type": "short_technical",
    "bm25_results_count": 50,
    "embedding_results_count": 50,
    "hybrid_results_count": 10
  }
}
```

#### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

#### Anomali İstatistikleri

```bash
curl http://localhost:8000/api/v1/anomaly/stats
```

## Proje Yapısı

```
bt-support-assistant/
├── app/                      # FastAPI uygulaması
│   ├── main.py              # Ana uygulama giriş noktası
│   ├── config.py            # Yapılandırma yönetimi
│   └── routers/             # API endpoint'leri
│       ├── chat.py          # Chat endpoint'i
│       ├── health.py        # Health check endpoint'i
│       └── anomaly.py        # Anomali tespiti endpoint'i
│
├── core/                     # Ana iş mantığı modülleri
│   ├── retrieval/           # Arama modülleri
│   │   ├── bm25_retriever.py        # BM25 arama
│   │   ├── embedding_retriever.py   # Embedding arama
│   │   ├── hybrid_retriever.py      # Hibrit arama
│   │   └── dynamic_weighting.py    # Dinamik ağırlıklandırma
│   │
│   ├── rag/                 # RAG pipeline
│   │   ├── pipeline.py      # Ana RAG pipeline
│   │   ├── prompts.py       # Prompt oluşturma
│   │   └── confidence.py   # Güven skoru hesaplama
│   │
│   ├── anomaly/             # Anomali tespiti
│   │   ├── engine.py        # Anomali tespit motoru
│   │   ├── detector.py      # Anomali dedektörü
│   │   └── drift_detector.py # Drift tespiti
│   │
│   └── nlp/                 # NLP modülleri
│       ├── preprocessing.py # Metin ön işleme
│       ├── intent.py        # Niyet tespiti
│       └── it_relevance.py  # IT ilgisi kontrolü
│
├── data_pipeline/            # Veri işleme
│   ├── ingestion.py         # Veri yükleme
│   ├── anonymize.py         # PII anonimleştirme
│   ├── build_indexes.py     # İndeks oluşturma
│   └── anomaly_job.py       # Anomali işleri
│
├── frontend/                 # Web arayüzü
│   ├── index.html           # Ana HTML
│   ├── app.js               # JavaScript mantığı
│   └── styles.css           # CSS stilleri
│
├── scripts/                  # Yardımcı script'ler
│   ├── run_server.py        # Sunucu başlatma
│   ├── build_and_test_index.py  # İndeks oluşturma ve test
│   ├── run_chat_scenarios.py    # Senaryo testleri
│   └── test_system.py       # Sistem testleri
│
├── tests/                    # Test dosyaları
│   ├── test_retrieval.py     # Arama testleri
│   ├── test_rag_pipeline.py  # RAG pipeline testleri
│   └── test_anomaly.py      # Anomali testleri
│
├── data/                     # Veri dosyaları
│   ├── raw/                 # Ham veriler
│   └── processed/           # İşlenmiş veriler
│
├── indexes/                  # Oluşturulan indeksler
│   ├── bm25_index.pkl       # BM25 indeksi
│   ├── faiss_index.bin      # FAISS vektör indeksi
│   └── embedding_data.pkl  # Embedding verileri
│
├── requirements.txt          # Python bağımlılıkları
├── pytest.ini              # Pytest yapılandırması
└── README.md               # Bu dosya
```

## Test Etme

### Senaryo Testleri

Önceden tanımlanmış senaryoları test etmek için:

```bash
# Önce sunucuyu başlatın (başka bir terminalde)
python scripts/run_server.py

# Senaryo testlerini çalıştırın
python scripts/run_chat_scenarios.py
```

Test senaryoları:
- Outlook şifre sıfırlama
- VPN bağlantı sorunu
- Yazıcı yazdırmıyor
- Laptop yavaş çalışıyor
- Email gönderemiyorum
- Disk dolu hatası

### Birim Testleri

```bash
pytest tests/
```

Belirli bir test modülünü çalıştırmak için:

```bash
pytest tests/test_retrieval.py -v
```

### Sistem Testi

```bash
python scripts/test_system.py
```

## Yapılandırma

### Dinamik Ağırlıklandırma Ayarları

`app/config.py` dosyasında dinamik ağırlıklandırma parametrelerini ayarlayabilirsiniz:

```python
# Varsayılan alpha değeri (dinamik ağırlıklandırma kapalıysa)
hybrid_alpha: float = 0.5

# KB doküman boost faktörü
kb_boost_enabled: bool = True
kb_boost_factor: float = 1.15  # %15 boost
```

### Güven Skoru Eşikleri

```python
# Minimum güven skoru (altında cevap verilmez)
confidence_threshold: float = 0.7
```

### LLM Ayarları

Gerçek LLM kullanmak için `.env` dosyasında:

```env
USE_REAL_LLM=true
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-4o-mini  # veya gpt-4o, gpt-4-turbo
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=1500
```

## Sorun Giderme

### İndeksler Yüklenmiyor

1. İndekslerin oluşturulduğundan emin olun: `python scripts/build_and_test_index.py`
2. `indexes/` klasöründe dosyaların varlığını kontrol edin
3. Dosya izinlerini kontrol edin

### Sunucu Başlamıyor

1. Port 8000'in kullanımda olup olmadığını kontrol edin
2. `app/config.py` dosyasında farklı bir port belirleyin
3. Gerekli bağımlılıkların yüklü olduğundan emin olun

### Düşük Güven Skorları

1. İndekslerin güncel olduğundan emin olun
2. Sorguların BT ile ilgili olduğundan emin olun
3. `confidence_threshold` değerini geçici olarak düşürebilirsiniz (test için)

### Embedding Model Yüklenmiyor

1. İnternet bağlantınızı kontrol edin (model ilk kez indirilecek)
2. `sentence-transformers` paketinin yüklü olduğundan emin olun
3. Disk alanını kontrol edin (model ~100MB yer kaplar)

## Performans İpuçları

- **İndeks Boyutu**: Büyük veri setleri için FAISS indeksini disk üzerinde tutun
- **Top-K Değeri**: Varsayılan `top_k=10` değerini ihtiyacınıza göre ayarlayın
- **Batch İşleme**: Çoklu sorgu için batch endpoint kullanın
- **Caching**: Sık kullanılan sorgular için cache mekanizması ekleyebilirsiniz

## Katkıda Bulunma

Bu proje TÜBİTAK destekli bir araştırma projesidir. Katkılarınız için:

1. Issue açarak hata bildirebilirsiniz
2. Pull request göndererek iyileştirmeler önerebilirsiniz
3. Dokümantasyon iyileştirmeleri yapabilirsiniz

## Lisans

Bu proje TÜBİTAK destekli bir araştırma projesidir. Ticari kullanım için lisans bilgileri için proje yöneticisi ile iletişime geçin.

## İletişim

Sorularınız ve önerileriniz için proje ekibi ile iletişime geçebilirsiniz.

## Sürüm Geçmişi

### v0.1.0 (2025-01-17)
- İlk stabil sürüm
- Hibrit arama sistemi
- Dinamik ağırlıklandırma
- Anomali tespiti modülü
- Web arayüzü
- KVKK uyumlu anonimleştirme
