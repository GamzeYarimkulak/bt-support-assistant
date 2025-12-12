# BT Support Assistant – Context-Aware Hybrid RAG & Anomaly Detection

Bu proje, **Kurumsal BT yardım masaları** için güvenilir, izlenebilir ve proaktif uyarı verebilen bir yapay zekâ destekli sistemdir.

## 🎯 Ana Hedefler

1. **Güvenilir Soru-Cevap:** ITSM ticket'ları ve iç dokümanlar üzerinden doğru yanıtlar
2. **Anomali Tespiti:** Zaman içindeki içerik değişimlerini izleyerek erken uyarı

## ✨ Temel Özellikler

- ✅ **Hibrit Arama:** BM25 (kelime) + Embedding (anlam) + Dinamik Ağırlıklandırma
- ✅ **"Kaynak Yoksa Cevap Yok" İlkesi:** Güvenilir kaynak olmadan cevap vermez
- ✅ **Güven Skoru:** Her yanıt için güvenilirlik skoru
- ✅ **Anomali Tespiti:** Yeni konu grupları ve içerik kaymalarını tespit eder
- ✅ **KVKK Uyumu:** PII anonimleştirme
- ✅ **Türkçe Teknik Dil:** Türkçe-İngilizce karışık sorgular desteklenir
- ✅ **IT Dışı Filtreleme:** BT ile ilgili olmayan sorular reddedilir

## 🚀 Hızlı Başlangıç

### 1. Conda Ortamı Oluşturun

```cmd
cd C:\Users\gamze.yarimkulak\Desktop\bt-support-assistant
C:\Users\gamze.yarimkulak\AppData\Local\anaconda3\Scripts\activate.bat base
conda activate bt-support
```

### 2. Paketleri Kurun

```cmd
pip install -r requirements.txt
```

### 3. İndeksleri Oluşturun

```cmd
python scripts/build_and_test_index.py
```

### 4. Server'ı Başlatın

```cmd
python scripts/run_server.py
```

### 5. Web Arayüzünü Açın

Tarayıcıda: `http://localhost:8000`

## 📋 Proje Yapısı

```
bt-support-assistant/
├── app/                    # FastAPI uygulaması
│   ├── main.py            # Ana uygulama
│   ├── config.py          # Ayarlar
│   └── routers/          # API endpoint'leri
├── core/                   # Ana modüller
│   ├── retrieval/         # Hibrit arama (BM25 + Embedding)
│   ├── rag/               # RAG pipeline
│   ├── anomaly/           # Anomali tespiti
│   └── nlp/               # NLP ve IT filtreleme
├── data_pipeline/          # Veri işleme
│   ├── ingestion.py       # Veri yükleme
│   ├── anonymize.py       # PII anonimleştirme
│   └── build_indexes.py   # İndeks oluşturma
├── frontend/              # Web arayüzü
├── scripts/               # Yardımcı script'ler
└── tests/                 # Test dosyaları
```

## 🔧 Kullanım

### Web Arayüzü

1. `http://localhost:8000` adresini açın
2. Chat sekmesinde sorunuzu yazın
3. Yanıt ve kaynakları görün
4. Debug bilgilerini inceleyin

### API Kullanımı

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "VPN bağlantı sorunu", "language": "tr"}'
```

## 📊 Proje Gereksinimleri

| Gereksinim | Durum |
|------------|-------|
| Hibrit Arama (BM25 + Embedding) | ✅ |
| Dinamik Ağırlıklandırma | ✅ |
| "Kaynak Yoksa Cevap Yok" | ✅ |
| Güven Skoru | ✅ |
| Anomali Tespiti | ✅ |
| KVKK Uyumu | ✅ |
| Türkçe Teknik Dil | ✅ |
| IT Dışı Filtreleme | ✅ |

## 📚 Dokümantasyon

- **İndeks Oluşturma:** `INDEKS_OLUSTURMA_ACIKLAMA.md`
- **Model Bilgileri:** `MODEL_BILGILERI.md`
- **Proje Durumu:** `PROJE_DURUMU_ve_IYILESTIRMELER.md`
- **CMD Komutları:** `CMD_KOMUTLARI.md`
- **Dinamik Ağırlıklandırma:** `DINAMIK_AGIRLIKLANDIRMA_IMPLEMENTASYONU.md`

## 🔍 Özellikler

### Dinamik Ağırlıklandırma

Sorgu tipine göre otomatik ağırlık ayarlama:
- **Kısa teknik sorgular:** Embedding ağırlıklı (alpha ~0.2)
- **Orta sorgular:** Dengeli (alpha ~0.5)
- **Uzun sorgular:** BM25 ağırlıklı (alpha ~0.7)

### IT Dışı Filtreleme

BT ile ilgili olmayan sorular otomatik reddedilir:
- "Şişeyi açamıyorum" → Reddedilir
- "VPN bağlantı" → Kabul edilir

### Debug Bilgileri

Her yanıtta görüntülenir:
- Dinamik Alpha değeri
- Sorgu tipi
- BM25/Embedding/Hibrit sonuç sayıları

## 🧪 Test

```cmd
# Sistem testi
python scripts/test_system.py

# Dinamik ağırlıklandırma testi
python scripts/test_dynamic_weighting_demo.py

# Retrieval testi
python scripts/test_retrieval_with_dynamic.py
```

## 🧪 Senaryo Testleri

Aşağıdaki senaryolar test edilir:

| Senaryo | Soru | Min Güven | Beklenen Anahtar Kelimeler |
|----------|------|-----------|---------------------------|
| **Outlook Şifre Sıfırlama** | "Outlook şifremi unuttum" | 0.4 | outlook, parola, şifre, sıfırlama |
| **VPN Bağlantı Sorunu** | "VPN'e bağlanamıyorum" | 0.4 | vpn, bağlantı, ayar, istemci |
| **Yazıcı Çalışmıyor** | "Yazıcı yazdırmıyor" | 0.3 | yazıcı, sürücü, bağlantı |
| **Yavaş Laptop** | "Laptop çok yavaş" | 0.3 | performans, disk, güncelleme |
| **Email Gönderemiyorum** | "Email gönderemiyorum" | 0.3 | email, mail, gönder, ayar |
| **Disk Dolu Hatası** | "Disk alanı doldu" | 0.35 | disk, alan, temizlik, dosya |

### Başarı Kriterleri

Bir senaryo **geçer** eğer:
1. **Güven** ≥ minimum eşik (senaryoya göre 0.3-0.4)
2. **Anahtar Kelimeler** ≥ beklenen anahtar kelimelerin %50'si cevapta görünür (büyük/küçük harf duyarsız)
3. **Kaynaklar** ≥ en az 1 kaynak döküman döndürülür

### Yeni Senaryo Ekleme

Özel senaryolar eklemek için `scripts/run_chat_scenarios.py` dosyasını düzenleyin:

```python
SCENARIOS.append(
    ChatScenario(
        name="Özel Senaryo",
        question="Sorunuz burada",
        expected_keywords=["anahtar1", "anahtar2", "anahtar3"],
        min_confidence=0.4,
    )
)
```

Ardından script'i çalıştırarak sonuçları görün.

## 📝 Notlar

- Server çalışırken terminali kapatmayın
- Server'ı durdurmak için `Ctrl+C`
- İndeksler `indexes/` klasöründe saklanır
- `.env` dosyası UTF-8 encoding ile kaydedilmelidir

## 🔗 API Endpoints

- `GET /api/v1/health` - Sağlık kontrolü
- `POST /api/v1/chat` - Soru-cevap
- `GET /api/v1/anomaly/stats` - İstatistikler
- `POST /api/v1/anomaly/detect` - Anomali tespiti

## 📄 Lisans

Bu proje TÜBİTAK destekli bir araştırma projesidir.
