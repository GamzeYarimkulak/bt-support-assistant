# 📚 İndeks Oluşturma Süreci - Detaylı Açıklama

## 🎯 İndeks Nedir?

**İndeks**, arama yapabilmek için dokümanların hazırlanmış halidir. İki tür indeks oluşturuyoruz:

### 1. BM25 İndeksi (Kelime Tabanlı)
- **Ne yapar?** Dokümanları kelimelere ayırır ve her kelimenin önemini hesaplar
- **Nasıl çalışır?** "Outlook şifre" sorgusu → "outlook" ve "şifre" kelimelerini içeren dokümanları bulur
- **Dosya:** `indexes/bm25_index.pkl`

### 2. Embedding İndeksi (Anlam Tabanlı)
- **Ne yapar?** Her dokümanı sayısal vektöre (embedding) dönüştürür
- **Nasıl çalışır?** "Outlook şifre" sorgusu → Anlam olarak benzer dokümanları bulur (örn: "email parola", "hesap giriş")
- **Dosya:** `indexes/faiss_index.bin` + `indexes/embedding_data.pkl`

## 📋 İndeks Oluşturma Adımları (Detaylı)

### Adım 1: CSV'den Veri Yükleme
```python
tickets = load_itsm_tickets_from_csv("data/sample_itsm_tickets.csv")
```
**Ne olur?**
- CSV dosyası okunur
- Her satır bir `ITSMTicket` nesnesine dönüştürülür
- Tarih, kategori, açıklama gibi alanlar parse edilir

**Örnek CSV satırı:**
```csv
TCK-0001,2024-12-01 09:15:00,Uygulama,Outlook,"Outlook şifremi unuttum","Kullanıcı Outlook'a giriş yapamıyor...","Şifre sıfırlama bağlantısı gönderildi",portal,Medium,Closed
```

### Adım 2: Anonimleştirme (KVKK)
```python
anonymized_tickets = anonymize_tickets(tickets)
```
**Ne olur?**
- Email adresleri → `[EMAIL]`
- Telefon numaraları → `[PHONE]`
- IP adresleri → `[IP]`
- İsimler → `[NAME]`

**Örnek:**
- Önce: "Kullanıcı ahmet@example.com şifresini unutmuş"
- Sonra: "Kullanıcı [EMAIL] şifresini unutmuş"

### Adım 3: Doküman Formatına Dönüştürme
```python
documents = convert_ticket_to_document(ticket)
```
**Ne olur?**
Her ticket şu formata dönüştürülür:
```python
{
    "text": "Outlook şifremi unuttum Kullanıcı Outlook'a giriş yapamıyor... Çözüm: Şifre sıfırlama bağlantısı gönderildi",
    "ticket_id": "TCK-0001",
    "short_description": "Outlook şifremi unuttum",
    "description": "...",
    "resolution": "...",
    "category": "Uygulama",
    ...
}
```

**Önemli:** `text` alanı tüm metinleri birleştirir (title + description + resolution)

### Adım 4: BM25 İndeksi Oluşturma
```python
bm25_retriever = IndexBuilder.build_bm25_index(documents)
```

**Süreç:**
1. **Tokenizasyon:** Her doküman kelimelere ayrılır
   - "Outlook şifre sıfırlama" → ["outlook", "şifre", "sıfırlama"]
2. **BM25 Hesaplama:** Her kelime için ağırlık hesaplanır
   - Sık geçen kelimeler (örn: "ve", "ile") düşük ağırlık
   - Nadir geçen kelimeler (örn: "VPN", "Outlook") yüksek ağırlık
3. **İndeks Kaydetme:** `indexes/bm25_index.pkl` dosyasına kaydedilir

**Örnek:**
```
Doküman: "Outlook şifre sıfırlama"
BM25 İndeksi:
  "outlook" → [TCK-0001: 2.5, TCK-0005: 1.8, ...]
  "şifre" → [TCK-0001: 3.2, TCK-0009: 2.1, ...]
```

### Adım 5: Embedding İndeksi Oluşturma
```python
embedding_retriever = IndexBuilder.build_embedding_index(documents)
```

**Süreç:**
1. **Model Yükleme:** `sentence-transformers/all-MiniLM-L6-v2` modeli indirilir/yüklenir
   - İlk kez: Model Hugging Face'den indirilir (~80 MB)
   - Sonraki: Yerel cache'den yüklenir
2. **Embedding Hesaplama:** Her doküman 384 boyutlu vektöre dönüştürülür
   ```
   "Outlook şifre sıfırlama" 
   → [0.12, -0.45, 0.78, ..., 0.23] (384 sayı)
   ```
3. **FAISS İndeksi:** Hızlı arama için FAISS indeksine eklenir
4. **Kaydetme:** 
   - `indexes/faiss_index.bin` (FAISS indeksi)
   - `indexes/embedding_data.pkl` (dokümanlar + embedding'ler)

**Örnek:**
```
Doküman: "Outlook şifre sıfırlama"
Embedding: [0.12, -0.45, 0.78, ..., 0.23] (384 boyut)
FAISS: Bu vektör indekse eklenir
```

## 🔍 Arama Nasıl Çalışır?

### Senaryo: Kullanıcı "Outlook şifremi unuttum" sorgusu yapar

#### 1. BM25 Arama (Kelime Tabanlı)
```
Sorgu: "Outlook şifremi unuttum"
Tokenize: ["outlook", "şifremi", "unuttum"]

Her doküman için:
- "outlook" kelimesi var mı? → Skor: +2.5
- "şifre" kelimesi var mı? → Skor: +3.2
- "unuttum" kelimesi var mı? → Skor: +1.8

Toplam Skor: 7.5 → TCK-0001 (en yüksek)
```

#### 2. Embedding Arama (Anlam Tabanlı)
```
Sorgu: "Outlook şifremi unuttum"
Embedding: [0.15, -0.42, 0.81, ..., 0.19] (384 boyut)

Her doküman embedding'i ile cosine similarity:
- TCK-0001: 0.92 (çok benzer!)
- TCK-0005: 0.78 (benzer)
- TCK-0009: 0.65 (orta)

En yüksek: TCK-0001
```

#### 3. Hibrit Arama (Dinamik Ağırlıklandırma ile)
```
Sorgu: "Outlook şifremi unuttum"
Analiz: Kısa teknik sorgu → Alpha = 0.3 (embedding ağırlıklı)

BM25 skoru: 7.5 → normalize → 0.85
Embedding skoru: 0.92

Hibrit skor = 0.3 * 0.85 + 0.7 * 0.92 = 0.90

Sonuç: TCK-0001 (en yüksek hibrit skor)
```

## 📊 İndeks Dosyaları

İndeks oluşturulduktan sonra `indexes/` klasöründe:

```
indexes/
├── bm25_index.pkl          # BM25 indeksi (kelime tabanlı)
├── embedding_data.pkl       # Embedding verileri (dokümanlar + vektörler)
├── faiss_index.bin         # FAISS indeksi (hızlı arama)
└── index_metadata.json      # İndeks bilgileri (kaç doküman, hangi model, vb.)
```

## ⏱️ Süreç Ne Kadar Sürer?

- **10 ticket:** ~1-2 dakika
- **100 ticket:** ~3-5 dakika
- **1000 ticket:** ~10-15 dakika

**Neden bu kadar sürer?**
- Embedding modeli ilk kez indiriliyor (~80 MB)
- Her doküman için embedding hesaplanıyor (384 boyut)
- FAISS indeksi oluşturuluyor

## 🔄 İndeks Yenileme

Yeni ticket'lar eklendiğinde:
```bash
python scripts/build_sample_index.py data/new_tickets.csv indexes/
```

Eski indeksler üzerine yazılır (güncellenir).

## ✅ İndeks Oluşturma Kontrolü

İndeks başarıyla oluşturuldu mu kontrol etmek için:
```python
from data_pipeline.build_indexes import IndexBuilder

builder = IndexBuilder(index_dir="indexes/")
bm25 = builder.load_bm25_index()
embedding = builder.load_embedding_index()

if bm25 and embedding:
    print("✅ İndeksler başarıyla yüklendi!")
    print(f"   BM25: {bm25.get_index_stats()['num_documents']} doküman")
    print(f"   Embedding: {embedding.get_index_stats()['num_documents']} doküman")
```


