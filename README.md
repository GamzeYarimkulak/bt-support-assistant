# BT Support Assistant – Context-Aware Hybrid RAG & Anomaly Detection

This repository contains a **context-aware IT support assistant** for an enterprise ITSM environment.  
The assistant has two main goals:

1. **Reliable Question Answering** over ITSM tickets and internal documentation  
2. **Anomaly & Drift Detection** over incoming IT tickets and their semantic distributions

The system is designed with strong constraints against hallucinations:  
> If there is not enough trusted evidence in the retrieved context, the model must explicitly say it cannot answer.

---

## High-Level Architecture

### Online path (user query → answer)

1. **User Interface**
   - Web chat / portal or embedded chat inside ITSM tool
2. **API Backend** (`app/`)
   - FastAPI application exposing chat and anomaly endpoints
   - Handles auth, sessions, logging, routing
3. **NLP & Intent** (`core/nlp/`)
   - Language detection, normalization, optional intent classification
4. **Hybrid Retrieval** (`core/retrieval/`)
   - BM25 (lexical) + embedding-based dense retrieval
   - Fusion to get top-k relevant tickets/docs
5. **RAG Answering** (`core/rag/`)
   - Given the retrieved context and user query, run a local LLM
   - Apply "no source, no answer" policy with confidence scoring
6. **Logging & Metrics**
   - Store logs and feedback for later evaluation and model improvement

### Offline path (data ingestion → indexes → anomaly features)

1. **Data Ingestion** (`data_pipeline/`)
   - Pull ITSM tickets and internal documentation
2. **Anonymization & Cleaning** (`data_pipeline/anonymize.py`)
   - Remove or mask PII (names, emails, phones, IPs, etc.)
3. **Index & Embeddings Build** (`data_pipeline/build_indexes.py`)
   - Build/update BM25 index
   - Compute embeddings and build/update vector index
4. **Anomaly Features** (`core/anomaly/`)
   - Aggregate embeddings and counts per time window
   - Compute drift/anomaly scores

---

## Repository Structure

- `app/`
  - `main.py`: FastAPI application entry point
  - `routers/`: API endpoints for chat, health, anomaly
  - `config.py`: configuration handling (env vars, paths, model names)
- `core/`
  - `nlp/`: preprocessing and intent classification
  - `retrieval/`: BM25, embedding, hybrid retrieval, evaluation metrics
  - `rag/`: RAG pipeline, prompts, confidence estimation
  - `anomaly/`: feature extraction, drift & anomaly detectors
- `data_pipeline/`: ITSM & docs ingestion, anonymization, index building
- `models/`: local model files (LLM and embedding models), not committed to git
- `scripts/`: helper scripts for development and evaluation
- `tests/`: unit tests

---

## Tech Stack

- **Language**: Python (3.11+)
- **API Framework**: FastAPI
- **Retrieval**:
  - BM25 via Elasticsearch/OpenSearch or a local Python-based solution
  - Dense retrieval via sentence-transformer-like embeddings + FAISS/hnswlib
- **RAG**:
  - Local LLM (e.g. 7B–8B models via `transformers` or compatible runtime)
- **Anomaly Detection**:
  - scikit-learn / simple statistical detectors
- **Evaluation**:
  - nDCG, Recall@k and similar retrieval metrics

---

## Principles

- **Safety first**: no hallucinated answers; answer "I don't know based on current sources" when evidence is insufficient.
- **Explainability**: always return which tickets/documents were used to generate an answer.
- **Privacy**: all ITSM data is anonymized before indexing or training.

---

## Web UI (Phase 6)

A simple, lightweight web interface is available for demoing the system without external tools.

### Features

- **💬 Chat Panel**: Interactive RAG-based Q&A
  - Submit queries in Turkish or English
  - View answers with confidence scores
  - See source tickets with relevance scores
  
- **📊 Anomaly Panel**: Drift and anomaly detection dashboard
  - View window statistics and drift scores
  - Detect anomaly events (info/warning/critical)
  - Explore volume spikes, category shifts, and semantic drift

### How to Run

**1. Start the Backend:**

```bash
# Activate your conda environment
conda activate bt-support

# Run the FastAPI server
python scripts/run_server.py
```

The server starts at `http://localhost:8000`

**2. Open the Web UI:**

Open your browser and navigate to:

```
http://localhost:8000
```

or

```
http://localhost:8000/ui/index.html
```

The UI is served directly by FastAPI at the root path.

### Usage Examples

**Chat Example:**

1. Click the "💬 Chat (RAG)" tab
2. Enter a question: `"Outlook şifremi nasıl sıfırlarım?"`
3. Select language: `Türkçe`
4. Click "🚀 Gönder"
5. View:
   - Answer text
   - Confidence score (with color coding)
   - Source tickets with IDs and relevance scores

**Anomaly Example:**

1. Click the "📊 Anomali Tespiti" tab
2. Click "📊 İstatistikleri Yükle" to view window stats
3. Click "🚨 Anomalileri Yükle" to see detected anomalies
4. Explore:
   - Ticket volume trends
   - Category distribution changes
   - Semantic drift events

### Technical Details

**Frontend Stack:**
- Pure HTML/CSS/JavaScript (no build tools required)
- Fetch API for REST calls
- Located in `frontend/` directory

**API Integration:**
- POST `/api/v1/chat` - RAG-based question answering
- GET `/api/v1/anomaly/stats?days=7` - Window statistics
- GET `/api/v1/anomaly/detect?min_severity=info` - Anomaly events

**CORS:**
- Enabled for all origins (configure for production)
- Allows frontend to call backend APIs seamlessly

---

## Scenario-Based Evaluation

The system includes end-to-end scenario tests to verify that the chat endpoint returns reasonable answers for typical IT support questions.

### Running Scenario Tests

**Prerequisites:**
1. Server must be running at `http://localhost:8000`
2. Install dependencies: `pip install -r requirements.txt`

**Option 1: Manual Script (Detailed Output)**

Run the standalone script for a detailed, colored report:

```bash
# Start server in one terminal
python scripts/run_server.py

# Run scenarios in another terminal
python scripts/run_chat_scenarios.py
```

**Output Example:**
```
✅ Outlook Şifre Sıfırlama
   Question: Outlook şifremi unuttum, nasıl sıfırlarım?
   Confidence: 0.67 (threshold: 0.40) ✓
   Keywords: 4/5 (80%) ✓
             outlook ✓, parola ✓, şifre ✓, sıfırlama ✓, bağlantı ✗
   Sources: 3 documents
   Answer length: 342 chars

SUMMARY
Total scenarios: 6
Passed: 5
Failed: 1
Pass rate: 83%
```

**Option 2: Pytest (Automated Testing)**

Run as part of the test suite:

```bash
# Run only integration tests
pytest tests/test_chat_scenarios.py -v -m integration

# Run all tests including scenarios
pytest -v
```

### Test Scenarios

The following scenarios are tested:

| Scenario | Question | Min Confidence | Expected Keywords |
|----------|----------|----------------|-------------------|
| **Outlook Password Reset** | "Outlook şifremi unuttum" | 0.4 | outlook, parola, şifre, sıfırlama |
| **VPN Connection Issue** | "VPN'e bağlanamıyorum" | 0.4 | vpn, bağlantı, ayar, istemci |
| **Printer Not Working** | "Yazıcı yazdırmıyor" | 0.3 | yazıcı, sürücü, bağlantı |
| **Slow Laptop** | "Laptop çok yavaş" | 0.3 | performans, disk, güncelleme |
| **Cannot Send Email** | "Email gönderemiyorum" | 0.3 | email, mail, gönder, ayar |
| **Disk Full Error** | "Disk alanı doldu" | 0.35 | disk, alan, temizlik, dosya |

### Success Criteria

A scenario **passes** if:
1. **Confidence** ≥ minimum threshold (0.3-0.4 depending on scenario)
2. **Keywords** ≥ 50% of expected keywords appear in answer (case-insensitive)
3. **Sources** ≥ at least 1 source document returned

### Adding New Scenarios

To add custom scenarios, edit `scripts/run_chat_scenarios.py`:

```python
SCENARIOS.append(
    ChatScenario(
        name="Custom Scenario",
        question="Your question here",
        expected_keywords=["keyword1", "keyword2", "keyword3"],
        min_confidence=0.4,
    )
)
```

Then run the script to see results.

---










/////////
Kurumsal Bilgi Teknolojileri (Bilgi Teknolojileri – BT) yardım masalarında biriken kayıtlar, çoğu zaman tekrarlayan sorunların erken fark edilmesini veya benzer taleplerin hızlıca çözüme yönlendirilmesini yeterince desteklememektedir. Ayrıca verilen yanıtların hangi bilgiye dayandığı ve ne kadar güvenilir olduğu çoğu zaman belirsizdir. Bu proje, bu eksikleri gidermek amacıyla güvenilir, izlenebilir ve gerektiğinde önceden uyarı verebilen bir yapay zekâ destekli sistem geliştirmeyi hedeflemektedir. Çalışmanın odak noktası, özellikle Türkçe ve Türkçe–İngilizce karışık teknik dilin yoğun kullanıldığı ortamlarda doğruluğun ve anlaşılabilirliğin artırılmasıdır.
Önerilen sistem, Bilgi Getirim Destekli Üretim (Retrieval-Augmented Generation – RAG) yaklaşımını kullanır. Sistem, hem kelime eşleşmesine dayalı arama hem de metnin anlamını dikkate alan arama yöntemlerini aynı anda çalıştırır. Bu iki yöntemin sonuçları birleştirilerek en uygun bilgi parçaları seçilir ve yanıtlar yalnızca bu doğrulanabilir içeriklere dayanarak üretilir. Yanıt üretiminde “kaynak yoksa cevap yok” ilkesi uygulanır. Böylece hatalı veya uydurma bilgi üretme riski azalır ve her yanıt kullanıcıya bir güven skoru ile sunulur.
Sistemin ikinci bileşeni, kayıtların zaman içindeki içerik değişimlerini izleyen bir bağlamsal anomali tespit modülüdür. Bu modül, kayıtların anlamsal yapısındaki değişimleri takip eder; yeni konu alanları oluştuğunda, mevcut konularda olağan dışı artış olduğunda veya beklenmeyen kaymalar ortaya çıktığında erken uyarı üreterek destek ekiplerinin kontrol sağlamasına yardımcı olur. Tüm veri işlemleri, Kişisel Verilerin Korunması Kanunu’na (KVKK) uygun şekilde anonimleştirilmiş içerik üzerinden gerçekleştirilecektir.
Proje; veri toplama ve anonimleştirme, hibrit arama yapısının oluşturulması, anlam temsili modellerinin kuruma uyarlanması, anomali tespit mekanizmasının geliştirilmesi, kaynak zorunlu yanıt üretimi ve geliştirilen prototipin pilot ortamda test edilmesi aşamalarından oluşmaktadır. Bu adımlar proje takvimine göre planlanmış olup her bir aşama ölçülebilir başarı ölçütleriyle takip edilecektir.
Projenin başarısı; bilgi getirimi doğruluğu, doğru kaydı bulma oranı, anomali tespit performansı, ortalama yanıt süresi ve tekrarlayan kayıt oranı gibi ölçütlerle değerlendirilecektir. Özdilek Holding Ar-Ge Merkezi ile yürütülecek pilot uygulamada, bilgi getirimi doğruluğunda hedeflenen seviyelere ulaşılması, anomali tespitinde yüksek doğruluk sağlanması, ortalama yanıt süresinin 2 saniyenin altında tutulması ve yineleyen kayıt oranında belirgin bir düşüş sağlanması beklenmektedir.

Sonuç olarak bu proje, Türkçe kurumsal veriler üzerinde çalışan, yanıtlarını kaynak göstererek üreten ve güvenilirlik skoru sunan yerli bir hibrit yapay zekâ sistemi ortaya koyacaktır. Geliştirilen sistem yalnızca BT yardım masalarında değil, bankacılık, telekomünikasyon ve e-ticaret gibi güçlü destek süreçleri bulunan farklı sektörlerde de uygulanabilir. Ayrıca proje sürecinde elde edilen teknik birikim, ileride hazırlanacak yeni TÜBİTAK proje başvuruları için değerli bir altyapı oluşturacaktır.
Anahtar Kelimeler: RAG, Hibrit Arama, Embedding Tabanlı Anomali Tespiti, LLM, BT Yardım Masası

1.	ARAŞTIRMA ÖNERİSİNİN BİLİMSEL NİTELİĞİ

1.1. Amaç ve Hedefler 

Araştırma önerisinde ele alınan konunun amacı, somut hedefleri ve sanayiye yönelik içeriği ortaya konulur. Önerilen konunun çözülmesi gereken ya da önceden çalışılmış aydınlatılması gereken bir problem olup olmadığı, hangi eksikliği nasıl gidereceği veya hangi sorunlara çözüm getireceği açıklanmalıdır. 

Bu projenin amacı, Bilgi Teknolojileri (BT) ortamlarında oluşan metin tabanlı destek kayıtlarını kullanarak doğru, güvenilir ve hızlı yanıtlar üretebilen bir yapay zekâ sistemi geliştirmektir. Sistem, yalnızca sorulara yanıt üretmekle kalmayacak; tekrarlayan sorunları ve olağandışı durumları da erken aşamada fark ederek kurumların reaktif yapıdan proaktif yapıya geçmesine katkı sağlayacaktır.
Proje, Bilgi Getirim Destekli Üretim (Retrieval-Augmented Generation – RAG) yöntemini, anlam değişimlerini takip eden bir anomali tespit yaklaşımıyla birleştirir. Böylece destek süreçlerinde hem doğruluk hem de izlenebilirlik artırılır. Çalışmanın odağı, uygulamaya dönük bir yapay zekâ çözümü sunarken teknik karmaşıklığı kurumların ihtiyaçlarına uygun düzeyde yönetmektir.
BT yardım masalarında öne çıkan temel sorunlar şunlardır:
Benzer taleplerin farklı yazım biçimleri nedeniyle sistem tarafından eşleşememesi,
Kayıtlardaki anlam değişimlerinin zaman içinde fark edilememesi ve hatalı sınıflandırmalara yol açması,
Verilen yanıtların hangi bilgiye dayandığının ve güvenilirlik düzeyinin belirsiz kalması.
Bu sorunlar hem çözüm sürelerini uzatmakta hem de yinelenen kayıt oranını artırmaktadır. Türkçe teknik ifadeler, kısaltmalar ve Türkçe–İngilizce karışık dil yapısı mevcut modeller için ek zorluklar oluşturur. Proje, bu etkiyi ortadan kaldırmayı hedeflemektedir.
Çalışma, Bursa Teknik Üniversitesi ile Özdilek Holding Ar-Ge Merkezi iş birliğinde, gerçek operasyon verileri kullanılarak yürütülecektir. Önerilen hibrit yapıda hem kelime temelinde arama hem de anlam temelli arama birlikte çalışır. Bu iki yöntemden elde edilen sonuçlar birleştirilerek en uygun bilgi seçilir ve yanıtlar yalnızca doğrulanabilir kaynaklara dayanır. Bu amaçla sistemde “kaynak yoksa cevap yok” ilkesi kullanılacaktır.
Projenin ikinci bileşeni, destek kayıtlarındaki içerik değişimlerini zaman içinde takip eden bir anomali tespit modülüdür. Bu modül, yeni konu gruplarının ortaya çıkması, belirli konularda ani yoğunluk artışı veya beklenmeyen içerik kaymaları olduğunda erken uyarı üretir. Bu sayede yaklaşan sorunlar henüz büyümeden fark edilebilir.
Sanayiye katkı iki boyutta ele alınmaktadır. Operasyonel olarak, doğru bilgiye daha hızlı ulaşılması sayesinde çözüm süresi kısalacak ve yinelenen kayıtlar azalacaktır. Yönetsel olarak ise konu yoğunlukları ve değişim trendleri izlenerek olası riskler önceden görülebilecek ve BT hizmet kalitesi artacaktır.
Projenin ölçülebilir hedefleri şunlardır:
Bilgi getirimi doğruluğunda belirlenen eşiğin (nDCG@10 ≥ 0,75) sağlanması,
Doğrulanabilir kaynağa dayanan yanıt oranının ≥ %70 olması,
Anomali tespitinde doğruluk (precision ≥ %80) ve yakalama oranının (recall ≥ %75) karşılanması,
İlk uyarının 45 dakika içinde üretilebilmesi,
Tekrarlayan kayıt oranında ≥ %60 azalma,
Güven skoru kalibrasyonunda belirgin iyileşme sağlanması.
Bu hedefler, yapılan ön analizler ve literatürdeki mevcut yöntemlerle uyumludur. Sonuçta proje, çözüm sürelerini kısaltan, maliyetleri azaltan ve veri gizliliğine uygun şekilde çalışan bir yapay zekâ altyapısı sunacaktır. Geliştirilen sistem sanayiye doğrudan devredilebilir nitelikte olup gelecekteki TÜBİTAK veya Avrupa Birliği proje başvuruları için ölçeklenebilir bir temel sağlayacaktır.
(*)Temel teknolojik alanlarda uzman kişilere sunulacağı dikkate alınarak değerlendirmeye hiçbir katkı sağlamayacak genel konu ve tarihçe anlatımlarından kaçınılmalıdır.


1.2.	Yenilikçi Yönü ve Teknolojik Değeri

Proje fikrinin ortaya çıkışından, hedeflenen ürünün veya sürecin özelliklerine kadar projenin endüstriyel Ar-Ge içeriği, teknoloji düzeyi ve yenilikçi yönü anlatılmalıdır. Projedeki yenilik unsurları ve proje çıktısının nitelikleri bakımından benzerlerinden farklı ve üstün olan yönleri somut verilerle ortaya konulmalıdır. 
Projenin konusu, 12. Kalkınma Planı ve 2030 Sanayi ve Teknoloji Stratejisi’nde yer alan kritik teknoloji alanları ile öncelikli Ar-Ge ve yenilik konuları ile ilişkili ise, ilişkilendirilme sebebi ve ilgili alana sağlayacağı yararlar açıklanmalıdır.

Bu projenin yenilikçi yönü, Bilgi Getirim Destekli Üretim (Retrieval-Augmented Generation – RAG) mimarisini, anlam temelli anomali tespiti ile birleştirerek Türkçe kurumsal veriler üzerinde çalışabilen özgün bir yapay zekâ sistemi geliştirmesidir. Mevcut sistemler çoğunlukla yalnızca bilgi getirimi veya yalnızca anomali tespiti işlevine odaklanmaktadır. Bu proje ise iki işlevi aynı yapı içinde birleştirerek BT (Bilgi Teknolojileri) yardım masası süreçlerini daha bütüncül bir şekilde ele almakta ve yazılım, ağ ve güvenlik bileşenlerinde ortaya çıkan sorunların daha erken fark edilmesine katkı sağlamaktadır. Bu sayede sistem, gelen taleplere yanıt vermenin ötesine geçerek yaklaşan sorunları önceden işaretleyen proaktif bir karar destek mekanizması sunmaktadır.
Piyasada yer alan ServiceNow, Zendesk ve Freshdesk gibi platformlar genellikle anahtar kelime aramalarına ve sabit yanıt şablonlarına dayalıdır. Microsoft Copilot veya Google Bard gibi genel amaçlı yapay zekâ çözümleri ise kurum içi veri gizliliği, Türkçe teknik terimler ve alan uyarlaması açısından sınırlıdır. Ayrıca bu sistemler çoğunlukla tek tip arama yöntemi kullandığı için serbest yazım ve teknik ifadelerin karıştığı sorgularda dengesizlik oluşmaktadır (Wang et al., 2024; Chen et al., 2024). Birçok Bilgi Getirim Destekli Üretim yaklaşımı ise dış kaynaklardan alınan içerikleri modele eklerken bağlam bütünlüğünü tam olarak koruyamamaktadır (Lewis et al., 2020). Bu proje, tüm bu sınırlamaları gideren, yerli, güvenilir ve bağlamsal bütünlüğü koruyan bir alternatif geliştirmektedir.
Özdilek Holding ile yapılan ön görüşmeler, BT destek süreçlerinde tekrarlanan kayıtların, yanlış yönlendirmelerin ve uzayan çözüm sürelerinin verimliliği düşürdüğünü göstermiştir. Projenin ilk aşamasında bu göstergeler kurum verisi üzerinde ölçülerek başlangıç durumu belirlenecek, ardından sistemin etkisi A/B testleriyle karşılaştırmalı olarak değerlendirilecektir. Geleneksel bilgi getirimi yöntemleri (örneğin BM25, TF-IDF) yalnızca kelime benzerliği üzerinden sonuç ürettiği için anlam ilişkilerini yeterince yakalayamamaktadır (Robertson et al., 1994). Klasik anomali tespiti yöntemleri de bağlamdaki değişiklikleri yakalama konusunda sınırlı kalmaktadır (Chalapathy & Chawla, 2019; Gama et al., 2014; Lu et al., 2019). Bu proje, hibrit Bilgi Getirim Destekli Üretim yaklaşımı ve Türkçe’ye uyarlanmış anlam temsili modelleri sayesinde bu sınırlamaları aşmayı hedeflemektedir. Pilot uygulamalarda tekrarlayan kayıt oranında %60 azalma ve anomali tespitinde %80 doğruluk (precision) beklenmektedir.
Teknik yenilik, hibrit arama yapısının, alan uyarlanmış anlam temsillerinin, “kaynak yoksa cevap yok” ilkesine dayalı yanıt üretiminin ve bağlamsal değişimleri izleyen anomali tespit modülünün sanayi koşullarında birlikte uygulanabilir hâle getirilmesidir. Sistem, farklı arama sonuçlarını ağırlıklandırılmış birleştirme yöntemiyle bir araya getirir; gerektiğinde yeniden sıralama uygulanarak yanıtların tutarlılığı artırılır. Destek kayıtlarındaki içerik değişimleri, zaman aralıkları üzerinden takip edilerek erken uyarı üreten bir yapı oluşturulur. Bu yaklaşım, hem güvenilir yanıt üretimini hem de proaktif izleme becerisini bir arada sunmaktadır (Asai et al., 2024).
Proje kapsamında geliştirilecek hibrit füzyon algoritması, mevcut sistemlerin çoğundan farklı olarak dinamik bağlam ağırlıkları kullanmaktadır. Çoğu yaklaşım sabit ağırlıklarla çalışırken, bu sistem sorgunun türüne ve içeriğine göre bağlam ağırlıklarını uyarlayarak hesaplamaktadır. Böylece özellikle kısa, teknik veya serbest ifadeli sorgularda doğrulukta anlamlı artış (nDCG@10 metriklerinde %10’a kadar) elde edilebilmektedir. Dinamik ağırlıklandırma ile “kaynak yoksa cevap yok” ilkesinin birlikte kullanılması, hem güvenilirliği hem de bağlamsal uygunluğu güçlendirmektedir. Bu nedenle geliştirilen yapının patentlenebilir nitelikte teknik yenilik unsurları bulunmaktadır.
Geliştirilen mimarinin yalnızca BT yardım masalarında değil, bankacılık, telekomünikasyon, e-ticaret, kamu hizmetleri gibi yoğun destek gerektiren sektörlerde de uygulanabilir olması, projenin yaygınlaştırılabilirliğini artırmaktadır. Sistemin yerel çalışabilen açık kaynaklı büyük dil modelleri (örneğin Llama 3.1-8B Instruct; Grattafiori et al., 2024; Mistral-7B; Jiang et al., 2023) üzerinde geliştirilmesi, veri gizliliğinin korunmasını sağlayacak ve ortalama yanıt süresinin 2 saniyenin altında tutulmasına imkân verecektir.
Proje, 12. Kalkınma Planı (2024–2028)’da yer alan “Yapay Zekâ ve Veri Odaklı Dönüşüm” ile “Dijital Teknolojilerde Yerli Üretim ve Beceri Geliştirme” önceliklerine doğrudan uyumludur. Türkçe teknik dilde çalışan bu sistem, veri gizliliğine duyarlı yerli yapay zekâ çözümlerine somut katkı sunacaktır. Ayrıca geliştirilen füzyon algoritması, güven skoru kalibrasyonu ve bağlamsal değişimlerin izlenmesine yönelik erken uyarı mekanizması, gelecekte patent veya faydalı model başvurularına konu olabilecek nitelikte yenilikler barındırmaktadır.
Sonuç olarak proje, Türkçe teknik destek süreçlerinde anlam farkındalığı, güvenilir yanıt üretimi ve anomali tespiti bileşenlerini bir araya getiren ilk yerli Ar-Ge prototiplerinden biridir. Bu yönüyle kurumsal ölçekte proaktif yapay zekâ tabanlı erken uyarı sistemlerine geçişte önemli bir örnek model oluşturmaktadır.


2.	YÖNTEM
Araştırmada uygulanacak analitik ve/veya deneysel çözüm yöntemleri, amaç ve hedeflere ulaşmaya ne düzeyde elverişli olduğu ilişkilendirilerek ve literatüre atıf yapılarak ortaya konulur. Araştırma önerisinde sunulan yöntemlerin çalışma takvimi ile ilişkilendirilmesi gerekir.

Bu çalışma, kurumsal destek kayıtları üzerinde RAG yöntemiyle dayanaklı yanıt üretimini ve anlam değişimlerini takip eden anomali tespitini tek bir yapı altında birleştirmektedir. Bu yaklaşımın amacı, tanımlanan hedeflerle uyumlu şekilde, hem doğru bilgiye dayalı yanıtlar üretmek hem de kayıt akışında ortaya çıkan olağandışı durumları erken aşamada fark etmektir. Genel mimari akış ve bileşenler arasındaki veri hareketi Şekil 1’de gösterilmiştir (Lewis et al., 2020; Robertson et al., 1994; Chalapathy & Chawla, 2019).
 
Şekil 1. Önerilen Hibrit RAG ve Semantik Drift/Kümelenme Tabanlı Anomali Tespit Sisteminin Genel Mimari Akışı
Araştırmanın temel girdileri; kurumun BT servis yönetim sistemi (ITSM) kayıtları, bilgi bankaları ve ilgili sistem günlükleri olacaktır. Bu verilere yalnızca yetkilendirilmiş servis hesapları ile erişilecek ve güvenli bağlantılar kullanılacaktır. Kayıtlar tarih, konu, hizmet kategorisi ve kaynak gibi bilgilerle etiketlenecektir. Kişisel veriler, Kişisel Verilerin Korunması Kanunu (KVKK) doğrultusunda anonimleştirilecek ve yalnızca içerik açısından işlenecektir. Bu adım, oluşturulacak prototipin gerçek ortamda uygulanabilirliği için gerekli veri kalitesini ve mevzuata uyumu sağlar. Veri hazırlama sürecinin adımları Şekil 2’de gösterilmiştir.
 
Şekil 2. Veri Hazırlama ve Paralel İndeksleme Süreci
Bir kullanıcı sorgusu geldiğinde sistem hem kelime temelli arama (BM25) hem de anlam temelli arama yöntemini aynı anda çalıştırır. Elde edilen sonuçlar birleştirilir ve gerekirse yeniden sıralama yapılır. Bu yapı, hem kısa ve teknik ifadeleri hem de serbest yazılmış sorguları daha dengeli şekilde karşılar ve RAG bileşeninin yüksek kaliteli bilgiye erişmesini sağlar (Robertson et al., 1994; Lewis et al., 2020).
Yanıt üretimi, “kaynak yoksa cevap yok” ilkesine göre yürütülür. Bu sayede sistem yalnızca doğrulanabilir kaynağa dayanan içerik üretir. Üretilen her yanıt, bir güven skoru ile birlikte sunulur ve bu skor kalibre edilir. Böylece yanlış bilgi (halüsinasyon) üretme riski azaltılır ve kullanıcıya daha güvenilir sonuçlar sağlanır (Asai et al., 2024).
Erken uyarı mekanizmasını oluşturan anomali tespit modülü, destek kayıtlarının anlam yapısını zaman içinde izler. Bu amaçla veri akışı belirli zaman pencerelerine bölünür; her penceredeki kayıtlar çok dilli veya alan uyarlanmış bir modelle sayısal temsillere dönüştürülür. Zaman pencereleri arasındaki dağılım kayması KL-divergence veya Wasserstein uzaklığı ile ölçülecek, anomali kümeleri ise k-means/DBSCAN tabanlı kümeleme ile belirlenecektir. Ardından kümeleme yöntemleri kullanılarak mevcut konu yapısı çıkarılır. Yeni konu gruplarının ortaya çıkması, mevcut konularda ani artışlar veya zaman pencereleri arasındaki belirgin değişimler anomali sinyali olarak değerlendirilir. Bu sinyaller mevsimsel değişimlerin ve veri gürültüsünün etkisini azaltacak yöntemlerle filtrelenir ve doğrulanan anomaliler “erken uyarı ve yönetim” paneline iletilir. Bu süreç Şekil 3’te gösterilmiştir (Gama et al., 2014; Lu et al., 2019).
 
Şekil 3. Semantik Drift ve Kümelenme Tabanlı Anomali Tespiti Akışı
Sistemin dinamik bağlam ağırlıkları, kullanıcının sorgusunun yapısına göre otomatik olarak uyarlanır. Örneğin “Outlook sürekli şifre istiyor” gibi anlam yoğunluklu bir sorguda, kelimeler sınırlı olsa bile semantik yapının güçlü olması nedeniyle anlam temelli arama hattının ağırlığı artırılır ve kelime temelli hattın ağırlığı azaltılır; böylece kelimesel olarak eşleşmeyen ancak teknik olarak doğru kayıtlar üst sıralara çıkar. Anomali tespitinde ise sistem, destek kayıtlarının zaman içindeki anlam dağılımını takip eder. Örneğin ardışık günlerde “VPN kopuyor”, “dış erişim başarısız”, “kimlik doğrulama döngü hatası” gibi semantik olarak benzer kayıtlar hızla birikirse, model zaman pencereleri arasındaki dağılım kaymasını ölçerek bu yeni yoğunluğu bir “anlam kümesi” olarak tespit eder ve olağandışı artışı erken uyarı olarak işaretler. Böylece mimari hem sorgu bazında doğru bağlamı seçerek yanıt doğruluğunu artırır hem de operasyonel akıştaki beklenmeyen anlam değişimlerini proaktif şekilde fark ederek kurumun erken müdahale kapasitesini güçlendirir.
Yöntemin başarısı hem çevrim dışı hem de çevrim içi değerlendirmelerle izlenecektir. Bilgi getirimi performansı nDCG@10 ve Recall@5 ölçütleriyle; anomali tespit başarımı ise doğruluk, yakalama oranı ve ilk uyarı süresiyle değerlendirilecektir. Ayrıca ortalama yanıt süresi, tekrarlayan kayıt oranı ve güven skoru kalibrasyonu da operasyon tarafında takip edilecektir. Beklenen seviyenin altında kalınan durumlarda yapılandırmalar gözden geçirilecek, kullanılan terim sözlüğü ve örnek havuzu güncellenecektir. Bu izleme ve iyileştirme döngüsü, proje hedeflerinin ölçülebilir şekilde doğrulanmasını sağlayacaktır.
