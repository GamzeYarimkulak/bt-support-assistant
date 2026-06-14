# Bölüm 5 Revize Çizelge ve Grafik Planı

Bu revize plan, çizelge sayısını azaltır ve örnek projedeki gibi metriklerin formül/açıklama tablosunu ekler.

## Gerçeklik Kontrolü

Grafikler ve çizelgeler manuel olarak uydurulmamıştır. Değerler aşağıdaki dosyalardan okunmuştur:

- Retrieval: `data/evaluation/retrieval/retrieval_metrics.json`
- Anomaly: `data/evaluation/anomaly/anomaly_validation_metrics.json`

Önemli sınırlılık: Bu sonuçlar gerçek Özdilek saha verisi üzerinde değil, mevcut proje veri seti, sentetik/curated anomaly validation verisi ve oluşturulan retrieval evaluation sorguları üzerinde elde edilmiştir. Raporda bu kapsam açıkça belirtilmelidir.

## Önerilen Nihai Çizelgeler

### Çizelge 5.1. Ölçüm Metrikleri ve Açıklamaları

| Metrik | Formül | 0-1 Arası Anlamı |
|---|---|---|
| Recall@k | `\|Retrieved@k ∩ Relevant\| / \|Relevant\|` | 1’e yaklaştıkça gerekli dokümanların daha fazlası ilk k sonuç içinde bulunur. |
| Precision@k | `\|Retrieved@k ∩ Relevant\| / k` | 1’e yaklaştıkça getirilen ilk k dokümanın daha büyük kısmı gerçekten ilgilidir. |
| nDCG@k | DCG@k / IDCG@k | 1’e yaklaştıkça doğru dokümanlar listenin daha üst sıralarında yer alır. |
| Category Hit@k | hit(expected_category, Retrieved@k) | 1’e yaklaştıkça sistem en az bir doğru kategori dokümanını ilk k sonuçta yakalar. |
| Subcategory Hit@k | hit(expected_subcategory, Retrieved@k) | 1’e yaklaştıkça daha dar alt kategori düzeyinde doğru sonuç yakalanır. |
| Event Precision | TP / (TP + FP) | 1’e yaklaştıkça üretilen anomaly eventlerinin daha azı yanlış alarmdır. |
| Event Recall | TP / (TP + FN) | 1’e yaklaştıkça gerçek anomaly eventlerinin daha fazlası yakalanır. |
| F1 | 2 × Precision × Recall / (Precision + Recall) | 1’e yaklaştıkça precision ve recall dengeli biçimde yüksek olur. |
| Specificity | TN / (TN + FP) | 1’e yaklaştıkça normal günler yanlış alarm üretilmeden normal bırakılır. |
| Severity Match | Doğru severity / eşleşen event | 1’e yaklaştıkça olay önem seviyesi ground-truth ile daha uyumludur. |

### Çizelge 5.2. Deney Veri Seti ve Değerlendirme Kapsamı

| Özellik | Değer |
|---|---:|
| Retrieval değerlendirme sorgusu | 180 |
| Başarılı retrieval sorgusu | 180 |
| Retrieval hata sayısı | 0 |
| İndekslenen doküman sayısı | 34975 |
| Anomali validation ticket sayısı | 3160 |
| Embedding içeren ticket sayısı | 3160 |
| Embedding boyutu | 384 |
| Toplam analiz penceresi | 182 |
| Evaluation aralığı | 2026-02-05 - 2026-07-06 |

### Çizelge 5.3. Retrieval Performans Sonuçları

| Metrik | Genel Sonuç | Ticket-spesifik | Genel kategori/alt kategori |
|---|---:|---:|---:|
| Sorgu sayısı | 180 | 100 | 80 |
| Recall@5 | 0.8500 | 0.9800 | 0.6875 |
| Recall@10 | 0.9111 | 1.0000 | 0.8000 |
| Precision@5 | 0.2422 | 0.1960 | 0.3000 |
| nDCG@10 | 0.7566 | 0.9204 | 0.5519 |
| Category Hit@5 | 0.9611 | 1.0000 | 0.9125 |
| Subcategory Hit@5 | 0.8611 | 1.0000 | 0.6875 |
| Ortalama gecikme (sn) | 0.4684 | - | - |

Not: Exact ID metrikleri yalnızca birebir `relevant_doc_ids` eşleşmesini ölçer. Genel destek sorguları için category/subcategory stratejisi daha gerçekçi kabul edilmiştir.

### Çizelge 5.4. Anomali Tespit Performans Sonuçları

| Metrik | Değer |
|---|---:|
| Ground-truth event | 39 |
| Detected event | 43 |
| Matched event / True Positive | 37 |
| False positive candidate | 6 |
| False negative | 2 |
| Event Precision | 0.8605 |
| Event Recall | 0.9487 |
| Event F1 | 0.9024 |
| Gün bazlı specificity | 0.9469 |
| Gün bazlı accuracy | 0.9474 |
| Gün bazlı balanced accuracy | 0.9478 |
| Severity exact match | 0.5405 |
| Score threshold | 0.30 |
| Warning / Critical eşik önerisi | 0.40 / 0.45 |

## Önerilen Nihai Grafikler

Çok fazla grafik koymak istemezsen 5 görsel yeterli olur:

| Şekil | Dosya | Neden gerekli? |
|---|---|---|
| Şekil 5.1 | `sekil_5_1_retrieval_metrikleri.png` | Retrieval performansını özetler. |
| Şekil 5.2 | `sekil_5_2_retrieval_strateji_karsilastirmasi.png` | Exact ticket ve genel kategori sorgularının farkını gösterir. |
| Şekil 5.3 | `sekil_5_4_anomali_model_kalitesi.png` | Anomaly model kalite sonuçlarını özetler. |
| Şekil 5.4 | `sekil_5_6_anomali_score_zaman_cizgisi.png` | Anomaly skorlarının zaman içindeki davranışını gösterir. |
| Şekil 5.5 | `sekil_5_7_gun_bazli_confusion_matrix.png` | Normal/anomali gün sınıflandırmasını net gösterir. |

Yedek/ek grafikler: latency histogramı, severity dağılımı ve threshold sweep grafiği ek sayfada veya kısa alt bölümde kullanılabilir.
