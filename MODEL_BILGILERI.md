# Kullanılan Modeller - Detaylı Bilgiler

## 📊 Embedding Model (Anlam Tabanlı Arama)

### Model: `sentence-transformers/all-MiniLM-L6-v2`

**Kaynak:** Hugging Face  
**Geliştirici:** Microsoft  
**Model Tipi:** Sentence Transformer (Encoder-only)

#### Teknik Özellikler:
- **Parametre Sayısı:** ~22.7M (22.7 milyon parametre)
- **Embedding Boyutu:** 384 boyut
- **Maksimum Sequence Length:** 256 token
- **Model Boyutu:** ~80 MB (indirildiğinde)
- **Dil Desteği:** Çok dilli (100+ dil, Türkçe dahil)

#### Performans:
- **Hız:** Çok hızlı (CPU'da ~1000 cümle/saniye)
- **Bellek:** Düşük (RAM'de ~200 MB)
- **Doğruluk:** Orta-iyi seviye (daha büyük modellere göre)

#### Kullanım Amacı:
- Doküman ve sorguları 384 boyutlu vektörlere dönüştürme
- Semantic (anlam) benzerliği hesaplama
- FAISS ile hızlı benzerlik araması

#### Alternatif Modeller (Daha İyi Performans İçin):
1. **`sentence-transformers/all-mpnet-base-v2`**
   - 110M parametre, 768 boyut
   - Daha iyi doğruluk, daha yavaş
   
2. **`intfloat/multilingual-e5-base`**
   - Çok dilli odaklı
   - Türkçe için daha iyi performans

3. **`paraphrase-multilingual-MiniLM-L12-v2`**
   - Çok dilli, 384 boyut
   - Türkçe için optimize edilmiş

---

## 🤖 LLM Model (Yanıt Üretimi)

### Şu Anki Durum: İki Seçenek Var

#### 1. OpenAI API (Şu An Aktif - PHASE 8)
**Model:** `gpt-4o-mini` (varsayılan)

**Teknik Özellikler:**
- **Parametre Sayısı:** Açıklanmamış (tahmin: ~1-2B)
- **Context Length:** 128K token
- **Maksimum Output:** 16K token
- **Dil Desteği:** Çok dilli (Türkçe dahil)
- **Maliyet:** Düşük (gpt-4o'ya göre %10-20)

**Alternatif OpenAI Modelleri:**
- `gpt-4o`: Daha güçlü, daha pahalı
- `gpt-4-turbo`: En güçlü, en pahalı
- `gpt-3.5-turbo`: Daha ucuz, daha zayıf

#### 2. Yerel Model (Yedek - Henüz Aktif Değil)
**Model:** `mistralai/Mistral-7B-Instruct-v0.2`

**Teknik Özellikler:**
- **Parametre Sayısı:** 7.24B (7.24 milyar parametre)
- **Context Length:** 32K token
- **Model Boyutu:** ~14 GB (quantized: ~4-7 GB)
- **Dil Desteği:** Çok dilli (Türkçe dahil)
- **Lisans:** Apache 2.0 (açık kaynak)

**Gereksinimler:**
- GPU: En az 8GB VRAM (16GB önerilir)
- RAM: En az 16GB
- Disk: ~14GB (full precision) veya ~7GB (quantized)

**Kullanım Durumu:**
- Şu anda `USE_REAL_LLM=false` olduğu için kullanılmıyor
- Stub (sahte) yanıt üreticisi kullanılıyor
- OpenAI API key varsa gerçek LLM kullanılabilir

---

## 📈 Model Karşılaştırması

| Özellik | Embedding (MiniLM) | LLM (gpt-4o-mini) | LLM (Mistral-7B) |
|---------|-------------------|-------------------|-------------------|
| **Parametre** | 22.7M | ~1-2B (tahmin) | 7.24B |
| **Boyut** | 80 MB | API (yok) | 14 GB |
| **Hız** | Çok Hızlı | Orta | Yavaş (yerel) |
| **Maliyet** | Ücretsiz | Düşük ($) | Ücretsiz |
| **Gizlilik** | Yerel | Bulut | Yerel |
| **Türkçe** | İyi | Mükemmel | İyi |

---

## 🔧 Model Ayarları (.env dosyasında)

```env
# Embedding Model
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# LLM Model (OpenAI)
USE_REAL_LLM=true
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# LLM Model (Yerel - henüz kullanılmıyor)
LLM_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.2
```

---

## 💡 Öneriler

### Embedding Model İçin:
- **Mevcut model yeterli** - Hızlı ve verimli
- Türkçe performansı artırmak için `paraphrase-multilingual-MiniLM-L12-v2` denenebilir
- Daha iyi doğruluk için `all-mpnet-base-v2` kullanılabilir (daha yavaş)

### LLM Model İçin:
- **Şu an için OpenAI API kullanımı önerilir** - Kolay ve etkili
- Yerel model sadece veri gizliliği kritikse gerekli
- Mistral-7B yerel kullanım için iyi bir seçenek

---

## 📚 Kaynaklar

- **Embedding Model:** https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- **Mistral-7B:** https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2
- **OpenAI Models:** https://platform.openai.com/docs/models



















