# BT Support Assistant Final Audit Raporu

Tarih: 11 Haziran 2026  
Kapsam: Kod, veri çıktıları, index çıktıları, evaluation çıktıları, smoke test ve TÜBİTAK başvuru hedefleriyle uyum analizi.

Bu rapor eski kök `.md` dosyalarına dayanmadan, mevcut kod dosyaları ve üretilmiş somut çıktılar üzerinden hazırlanmıştır.

## 1. Genel Sonuç

Proje, TÜBİTAK başvuru metnindeki ana teknik hedefleri prototip düzeyinde karşılar:

- Hibrit RAG hattı vardır: BM25 + FAISS/embedding tabanlı semantic retrieval.
- Ticket ve KB dokümanları aynı index hattına alınmıştır.
- Kaynak tabanlı yanıt üretimi ve güven skoru mantığı uygulanmıştır.
- Türkçe/karma teknik BT destek senaryoları için veri hazırlama ve evaluation setleri oluşturulmuştur.
- Bağlamsal anomali tespit modülü vardır: volume spike, category shift, semantic drift ve combined anomaly sinyalleri işlenmektedir.
- Bağımsız anomaly validation seti ile daha gerçekçi precision/recall/F1 ölçümü yapılmıştır.
- Web arayüzünde chat, anomaly stats/detect ve model quality paneli bulunmaktadır.
- Test ortamı çalışır durumdadır.

Final durum: Rapor yazımına başlanabilir. Yeni büyük özellik eklemek yerine metin, deney kurulumu ve sınırlılıkların doğru yazılması daha mantıklıdır.

## 2. TÜBİTAK Başvuru Hedefleriyle Uyum

Başvuru metnindeki ana hedefler şu şekilde özetlenebilir:

- BT destek kayıtlarından güvenilir ve hızlı yanıt üretmek.
- RAG ile kelime tabanlı ve anlam tabanlı aramayı birlikte kullanmak.
- Yanıtları doğrulanabilir kaynaklara dayandırmak.
- Güven skoru sunmak ve kaynak yoksa cevap üretmemek.
- Türkçe ve Türkçe-İngilizce karma teknik dilde çalışmak.
- Kayıt akışında olağan dışı hacim artışı, konu/kategori kayması ve anlamsal drift yakalamak.
- KVKK/anonimleştirme yaklaşımıyla veri işlemek.
- Bilgi getirimi doğruluğu, doğru kayıt bulma oranı, anomali performansı ve yanıt süresi gibi ölçütlerle değerlendirmek.
- Pilot veri idealde Özdilek ortamından gelecektir.

Mevcut uygulama bu hedeflerin çoğunu prototip olarak karşılıyor. Eksik kalan en önemli nokta gerçek Özdilek pilot verisinin olmamasıdır. Bu nedenle final metinde sistem "gerçek kurumsal veriyle doğrulanmış ürün" olarak değil, "açık/sentetik veriyle doğrulanmış çalışan prototip" olarak konumlandırılmalıdır.

## 3. Veri Durumu

Üretilmiş ana veri çıktıları:

- `data/processed/tickets.csv`
- `data/processed/tickets.parquet`
- `data/processed/kb_documents.csv`
- `data/processed/kb_chunks.jsonl`
- `data/processed/data_summary.json`

Satır/doküman durumu:

- Ham ticket satırı: 80.350
- Temizlik sonrası korunan ticket: 34.840
- Out-of-scope çıkarılan satır: 41.859
- Duplicate external text çıkarılan satır: 3.651
- KB dokümanı: 135
- KB chunk: 135
- `tickets.parquet` içinde embedding olan ticket: 34.840 / 34.840

Bu iyi bir durumdur. 80 bin ham satırın tamamını indexlememek zarar değil; veri temizleme sonrası BT kapsamıyla daha uyumlu ve tekrarları azaltılmış bir index oluşturulmuştur.

Veri kaynağı sınırlılığı:

- Özdilek verisi olmadığı için proje açık kaynak, dönüştürülmüş ve sentetik BT ticket verileriyle yürütülmektedir.
- Bu durum raporda açıkça yazılmalıdır.
- Bu veri seti yöntem doğrulama ve bitirme projesi demosu için yeterlidir, fakat saha performansı iddiası için yeterli değildir.

## 4. Index Durumu

Index çıktıları:

- `indexes/bm25_index.pkl`
- `indexes/embedding_data.pkl`
- `indexes/faiss_index.bin`
- `indexes/index_metadata.json`

Index metadata sonucu:

- Toplam indexlenen doküman: 34.975
- Ticket dokümanı: 34.840
- KB dokümanı/chunk: 135
- Limit kullanımı: false
- Embedding modeli: `sentence-transformers/all-MiniLM-L6-v2`
- Embedding boyutu: 384
- Ticket kaynağı: `data/processed/tickets.parquet`
- KB kaynağı: `data/processed/kb_chunks.jsonl`

Sonuç: Full index hattı tamamdır. Demo/test modu için `--limit` desteği var ama mevcut index full/temizlenmiş veriyle üretilmiş durumda.

## 5. Retrieval Evaluation Durumu

Evaluation dosyaları:

- `data/evaluation/retrieval/retrieval_eval_queries.csv`
- `data/evaluation/retrieval/retrieval_metrics.json`
- `data/evaluation/retrieval/retrieval_debug_top5.csv`

Son evaluation koşulu:

- Query sayısı: 180
- Başarılı query: 180
- Hata: 0
- Benzersiz query metni: 179
- Index: 34.975 dokümanlık full index

Son retrieval metrikleri:

- Exact Recall@5: 0.9800
- Exact Recall@10: 1.0000
- Exact Precision@5: 0.1960
- Exact nDCG@10: 0.9204
- Category Hit@5: 0.9611
- Category Hit@10: 0.9722
- Subcategory Hit@5: 0.8611
- Subcategory Hit@10: 0.9111
- Category Precision@5: 0.8833
- Subcategory Precision@5: 0.3356
- KB Hit@5: 0.0667
- Mean latency: 0.4684 sn

Yorum:

- Daha önce düşük gelen exact ID skoru evaluation setindeki tekrar/generic query probleminden kaynaklanıyordu.
- Şu anda exact ID evaluation seti daha iyi hizalanmış; 180 sorguda Recall@5 0.98 oldu.
- Category-aware metrikler de yüksek ve tutarlı.
- Precision@5'in 0.196 olması exact ID tanımı açısından normaldir; tek relevant doc beklenen sorguda top-5 içinde bir doğru doküman varsa precision teorik olarak 1/5 = 0.20 civarındadır.
- KB Hit@5 düşük; çünkü evaluation sorgularının büyük bölümü ticket retrieval odaklıdır. KB için ayrı KB-centric query seti hazırlanırsa bu metrik daha anlamlı olur.

## 6. Anomaly Evaluation Durumu

Anomaly tarafında iki farklı evaluation dosyası vardır:

- `data/evaluation/anomaly/anomaly_metrics.json`
- `data/evaluation/anomaly/anomaly_validation_metrics.json`

Ana processed veriyle yapılan eski/curated kontrol:

- Ground-truth event: 4
- Detected event: 37
- Precision: 0.1081
- Recall: 1.0000
- F1: 0.1951

Bu dosya final kalite iddiası için kullanılmamalıdır. Recall 1.0 görünse de yalnızca 4 pozitif pencereye dayandığı için yanıltıcıdır. Script bu durumu uyarı olarak belirtmektedir.

Bağımsız validation seti:

- Validation gün sayısı: 190
- Pozitif anomaly günü: 39
- Negatif gün: 151
- Validation ticket sayısı: 3.245
- Anomaly türleri: volume spike, category shift, semantic drift, combined anomaly
- Embedding modeli: `sentence-transformers/all-MiniLM-L6-v2`
- Embedding boyutu: 384

Son validation metrikleri:

- Ground-truth event: 39
- Detected event: 43
- Matched event: 37
- False positive candidate: 6
- Precision: 0.8605
- Recall: 0.9487
- F1: 0.9024
- Date-level recall: 0.9487
- Specificity: 0.9469
- TP days: 37
- FP days: 6
- FN days: 2
- TN days: 107
- Score threshold: 0.30
- Önerilen warning threshold: 0.40
- Önerilen critical threshold: 0.45

Yorum:

- Final rapora anomaly performansı olarak validation setindeki değerler yazılmalıdır.
- Bu metrikler hem pozitif hem negatif günleri içerdiği için daha gerçekçidir.
- Semantic drift artık ölçülebilir durumdadır çünkü validation ve processed ticket dosyalarında embedding alanı vardır.
- Severity exact match yaklaşık orta seviyededir; bu nedenle raporda severity sınıflandırması "geliştirilebilir" olarak yazılmalıdır.

## 7. Frontend ve Demo Durumu

Frontend dosyaları:

- `frontend/index.html`
- `frontend/styles.css`
- `frontend/app.js`

Arayüzde mevcut paneller:

- Destek Asistanı chat ekranı
- Anomaly stats ekranı
- Anomaly detect ekranı
- Alert / review candidate ayrımı
- Model Quality paneli

Model Quality paneli `GET /api/v1/anomaly/quality` endpointinden gerçek validation metriklerini okur. Panelde event precision, recall, F1, day F1, specificity, severity match ve false positive sayısı gösterilir.

Smoke test sonucu:

- `/` frontend: 200
- `/ui/styles.css`: 200
- `/ui/app.js`: 200
- `/api/v1/health`: 200
- `/api/v1/anomaly/quality`: 200
- `/api/v1/anomaly/stats`: 200
- `/api/v1/anomaly/detect`: 200
- `/api/v1/chat`: offline cache env ile 200
- `node --check frontend/app.js`: passed

Önemli demo notu:

- `frontend/app.js` içinde API base URL `http://localhost:8000` olarak sabit.
- Bu nedenle gerçek demoda backend `8000` portunda çalışmalıdır.
- Frontend başka porttan açılırsa bile API çağrıları `localhost:8000` backendine gider.

Önerilen demo komutu:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Sonra tarayıcı:

```text
http://127.0.0.1:8000/
```

Offline env notu:

- İlk smoke testte embedding modeli HuggingFace'e HEAD isteği atmaya çalıştığı için restricted sandbox ortamında chat endpoint 503 verdi.
- Aynı endpoint offline cache değişkenleriyle 200 döndü.
- Bu durum retrieval kod hatası değil, model loader'ın ağ kontrolü/dependency davranışıdır.

## 8. Test Durumu

Çalıştırılan komut:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
python -m pytest
```

Sonuç:

- 109 passed
- 9 skipped
- 3 warnings

Skipped testler canlı server gerektiren chat scenario integration testleridir. Unit ve pipeline testleri geçmektedir.

Uyarılar:

- Pydantic v2 deprecation uyarıları var.
- Bunlar şu an test kırmıyor; teslim öncesi kritik değil.

## 9. Gerekli, Opsiyonel ve Gereksiz Dosyalar

Gerekli çekirdek kod:

- `app/`
- `core/`
- `data_pipeline/`
- `scripts/prepare_data_for_indexing.py`
- `scripts/evaluate_retrieval.py`
- `scripts/evaluate_anomaly.py`
- `scripts/generate_anomaly_validation_data.py`
- `scripts/generate_tubitak_eval_data.py`
- `scripts/attach_ticket_embeddings.py`
- `frontend/`
- `tests/`
- `requirements.txt`
- `pytest.ini`

Gerekli veri ve çıktı dosyaları:

- `data/processed/`
- `data/evaluation/retrieval/`
- `data/evaluation/anomaly/`
- `indexes/`

Korunması önerilen raw/provenance dosyaları:

- `data/raw/tickets/`
- `data/raw/kb/`
- `data/logs/synthetic/`

Çünkü bu dosyalar processed çıktılarının nereden geldiğini göstermek için yararlı olabilir.

Opsiyonel temizlik adayları:

- `.pytest_cache/`
- `__pycache__/` klasörleri

Bu klasörler test/import sırasında oluşur; rapor ve kod için gerekli değildir.

Kökte eski `.md` dosyaları:

- Kök dizinde aktif `.md` dosyası kalmamış görünüyor.
- Git status içinde eski `.md` dosyaları silinmiş olarak görünüyor.
- Eski şişirilmiş içerikler geri getirilmemelidir.
- Teslim paketi için istenirse eski metinlerden bağımsız, kısa ve teknik bir README daha sonra yazılabilir.

Potansiyel legacy/yardımcı scriptler:

- `scripts/test_*.py`
- `scripts/comprehensive_test.py`
- `scripts/cleanup_unnecessary_files.py`
- `scripts/build_indexes.py`

Bunlar çekirdek çalışmayı bozmaz. Teslimde karışıklık yaratırsa `scripts/legacy/` altına taşınabilir; şu anda silinmesi şart değildir.

## 10. Eksikler ve Dürüst Sınırlılıklar

Gerçek kurumsal veri yok:

- Özdilek verisi alınamadığı için saha doğrulaması yoktur.
- Mevcut sonuçlar açık/sentetik/dönüştürülmüş veri üzerinde prototip doğrulamasıdır.

Pilot etkisi ölçülmedi:

- Ortalama çözüm süresi düşüşü, tekrar eden ticket oranı düşüşü ve gerçek kullanıcı kabul testi ölçülmedi.
- Bunlar raporda "gelecek çalışma / pilot aşama" olarak yazılmalıdır.

LLM üretimi:

- Sistem stub tabanlı advisory yanıt üretebiliyor.
- Gerçek OpenAI/LLM entegrasyonu için API anahtarı ve canlı değerlendirme gerekir.
- Buna rağmen kaynaklı yanıt, confidence ve no-source/no-answer mantığı prototip düzeyinde vardır.

Severity kalibrasyonu:

- Anomaly event yakalama güçlüdür.
- Severity exact match orta seviyededir.
- Warning/critical threshold kalibrasyonu eklendi ama gerçek kurum verisinde yeniden ayarlanmalıdır.

KB coverage:

- KB chunk sayısı 135 ile sınırlıdır.
- Retrieval evaluation daha çok ticket odaklıdır.
- KB başarımı için ayrıca KB ağırlıklı query seti hazırlanmalıdır.

Model bağımlılığı:

- Embedding modeli cachete varsa offline çalışır.
- Yeni ortamda ilk kurulumda model indirme gerekebilir.
- Demo öncesi model cache kontrolü yapılmalıdır.

## 11. Bitirme Raporuna Yazılacak Ana Cümleler

Proje, hibrit RAG ve anomali tespitini tek prototipte birleştirmiştir. Ticket kayıtları ve bilgi bankası dokümanları ortak bir index yapısında temsil edilmiş, BM25 ile kelime tabanlı eşleşme ve FAISS tabanlı embedding araması birlikte kullanılmıştır. Yanıt üretiminde kaynak zorunluluğu ve confidence skoru uygulanmıştır.

Veri tarafında ham 80.350 ticket satırı temizlenmiş, BT kapsamına uygun 34.840 ticket ve 135 KB chunk indexlenmiştir. Tüm ticket kayıtlarında embedding alanı bulunmaktadır. Bu sayede hem retrieval hem anomaly tarafı aynı veri temsili üzerinden çalışabilmektedir.

Retrieval evaluation 180 sorgu ile yapılmış, 180 sorgunun tamamı başarıyla tamamlanmıştır. Full index üzerinde Exact Recall@5 0.98, Exact nDCG@10 0.9204, Category Hit@5 0.9611 ve Category Precision@5 0.8833 elde edilmiştir. Ortalama retrieval latency 0.4684 saniyedir.

Anomaly tarafında final kalite iddiası, negatif günleri de içeren bağımsız validation seti üzerinden verilmiştir. 190 günlük validation akışında 39 pozitif anomaly günü ve 151 negatif gün üretilmiştir. Bu sette precision 0.8605, recall 0.9487, F1 0.9024 ve specificity 0.9469 elde edilmiştir.

Sistemin en önemli sınırlılığı gerçek Özdilek pilot verisinin kullanılamamasıdır. Bu nedenle sonuçlar gerçek saha performansı olarak değil, yöntemsel prototip doğrulaması olarak yorumlanmalıdır. Gerçek kurum verisiyle pilot çalışma, threshold kalibrasyonu, KB genişletme ve kullanıcı kabul testleri gelecek çalışma olarak bırakılmıştır.

## 12. Hazırlık Kararı

Rapor yazımına başlanabilir.

Kod ve çıktı durumu bitirme projesi için güçlü bir prototip seviyesindedir. TÜBİTAK metnindeki tüm büyük başlıklar çalışır bir sistemle temsil edilmektedir. Bundan sonraki en doğru iş, yeni özellik eklemek değil; yöntem, deney kurulumu, veri sınırlılığı ve sonuçları dürüst biçimde yazmaktır.


web:http://localhost:8000/