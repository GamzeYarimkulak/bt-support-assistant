# Data Pipeline Kullanım Rehberi

Bu rehber, yeni eklenen data pipeline script'lerinin nasıl kullanılacağını açıklar.

---

## 📁 Dizin Yapısı

Önce standart dizin yapısını oluşturun:

```bash
python scripts/init_data_dirs.py
```

Bu komut şu dizinleri oluşturur:
- `data/raw/tickets/` - CSV ticket dosyaları buraya
- `data/raw/kb/` - PDF KB dosyaları buraya
- `data/processed/` - İşlenmiş dosyalar buraya yazılır

**Not:** Mevcut CSV/PDF dosyalarınızı elle taşımanız gerekir. Script otomatik taşımaz.

---

## 1️⃣ Ticket Ingestion (CSV → Parquet)

CSV ticket dosyalarını standart parquet formatına dönüştürür.

### Kullanım

```bash
# Temel kullanım
python data_pipeline/ingest_tickets.py

# Özel input/output
python data_pipeline/ingest_tickets.py --input-dir data/raw/tickets --output data/processed/tickets.parquet

# Dry-run (sadece analiz, dosya yazmaz)
python data_pipeline/ingest_tickets.py --dry-run

# Test için limit
python data_pipeline/ingest_tickets.py --limit 100
```

### Çıktı

- `data/processed/tickets.parquet` - Standart şemalı parquet dosyası

### Şema

- `id`: str
- `text`: str (subject + body birleştirilmiş)
- `resolution`: str
- `category`: str
- `priority`: str
- `language`: str
- `created_at`: datetime veya None
- `source`: str (kaynak dosya adı)

### Özellikler

- Otomatik kolon mapping (farklı CSV formatlarını destekler)
- KVKK uyumu için anonimleştirme (settings.anonymization_enabled kontrol eder)
- Detaylı log ve rapor

---

## 2️⃣ KB Ingestion (PDF → JSONL)

PDF dosyalarını chunk'lara bölerek JSONL formatına dönüştürür.

### Kullanım

```bash
# Temel kullanım
python data_pipeline/ingest_kb.py

# Özel input/output
python data_pipeline/ingest_kb.py --input-dir data/raw/kb --output data/processed/kb_chunks.jsonl

# Dry-run
python data_pipeline/ingest_kb.py --dry-run

# Test için sayfa limiti
python data_pipeline/ingest_kb.py --max-pages 10

# Chunk boyutu ayarlama
python data_pipeline/ingest_kb.py --chunk-size 500
```

### Çıktı

- `data/processed/kb_chunks.jsonl` - Her satır bir chunk (JSON formatında)

### Şema (her chunk)

- `id`: str (unique chunk ID)
- `text`: str (chunk metni)
- `source_pdf`: str (kaynak PDF dosya adı)
- `page`: int (sayfa numarası)
- `chunk_index`: int (sayfa içindeki chunk indeksi)

### Özellikler

- ~400 token chunk boyutu (ayarlanabilir)
- Sayfa bazlı chunking
- Overlap desteği (chunk'lar arası geçiş)

### Gereksinimler

```bash
pip install pypdf
```

---

## 3️⃣ Index Build (Parquet + JSONL → Indexes)

İşlenmiş verilerden BM25 ve FAISS index'lerini oluşturur.

### Kullanım

```bash
# Temel kullanım
python scripts/build_indexes.py

# Özel dosya yolları
python scripts/build_indexes.py --tickets data/processed/tickets.parquet --kb data/processed/kb_chunks.jsonl

# Dry-run
python scripts/build_indexes.py --dry-run

# Test için limit
python scripts/build_indexes.py --limit 1000

# Mevcut index'leri yeniden oluştur
python scripts/build_indexes.py --rebuild
```

### Çıktı

- `indexes/bm25_index.pkl` - BM25 index
- `indexes/faiss_index.bin` - FAISS index
- `indexes/embedding_data.pkl` - Embedding data
- `indexes/index_metadata.json` - Metadata

### Özellikler

- Mevcut index'leri korur (--rebuild ile yeniden oluşturulabilir)
- Ticket ve KB chunk'larını birleştirir
- Mevcut IndexBuilder sınıfını kullanır (mevcut kodu bozmaz)

---

## 4️⃣ Retrieval Evaluation

Retrieval performansını ölçer (Recall@5, nDCG@10, latency).

### Kullanım

```bash
# Temel kullanım
python scripts/evaluate_retrieval.py

# Query sayısı ayarlama
python scripts/evaluate_retrieval.py --n-queries 200

# Random seed ayarlama
python scripts/evaluate_retrieval.py --seed 123

# Özel output dosyası
python scripts/evaluate_retrieval.py --output my_results.json
```

### Çıktı

- `test_results.json` - Evaluation sonuçları (JSON formatında)

### Metrikler

- **Recall@5**: İlk 5 sonuçta ground truth bulunma oranı
- **nDCG@10**: Normalized Discounted Cumulative Gain @ 10
- **Average Latency**: Ortalama sorgu süresi (saniye)

### Ground Truth

Basit yaklaşım: Ticket'ın `text` alanı sorgu, `resolution` alanı ground truth olarak kullanılır.

---

## 🔄 Tam Pipeline Örneği

```bash
# 1. Dizinleri oluştur
python scripts/init_data_dirs.py

# 2. CSV dosyalarını data/raw/tickets/ klasörüne taşı (elle)

# 3. PDF dosyalarını data/raw/kb/ klasörüne taşı (elle)

# 4. Ticket'ları işle
python data_pipeline/ingest_tickets.py

# 5. KB dosyalarını işle
python data_pipeline/ingest_kb.py

# 6. Index'leri oluştur
python scripts/build_indexes.py

# 7. Performansı ölç
python scripts/evaluate_retrieval.py
```

---

## ⚙️ Ayarlar

Tüm script'ler `app/config.py` içindeki settings'i kullanır:

- `settings.data_dir` - Veri dizini (default: "./data")
- `settings.anonymization_enabled` - Anonimleştirme açık/kapalı (default: True)
- `settings.embedding_model_name` - Embedding model (default: "sentence-transformers/all-MiniLM-L6-v2")

---

## 🐛 Sorun Giderme

### "pypdf not installed" hatası

```bash
pip install pypdf
```

### "Parquet file not found" hatası

Önce `ingest_tickets.py` çalıştırın.

### "Index files already exist" hatası

`--rebuild` flag'i ile yeniden oluşturun:
```bash
python scripts/build_indexes.py --rebuild
```

### Anonimleştirme çalışmıyor

`data_pipeline/anonymize.py` dosyasının mevcut olduğundan emin olun. Settings'te `anonymization_enabled=True` olmalı.

---

## 📝 Notlar

- Tüm script'ler `--dry-run` desteği ile güvenli test edilebilir
- Mevcut kod hiçbir şekilde değiştirilmedi, sadece yeni dosyalar eklendi
- Settings'ten path okunur, hardcode path yok
- Unit testler bozulmadı








