# B?l?m 5 G?rsel ve ?izelge Plan?

Bu dosya 5. b?l?mde kullan?labilecek tablo ve ?ekilleri ?zetler. Grafikler ayn? klas?rde PNG olarak ?retilmi?tir.

## ?nerilen ?ekiller

| ?ekil | Dosya | Kullan?m amac? |
|---|---|---|
| ?ekil 5.1 | `sekil_5_1_retrieval_metrikleri.png` | Retrieval katman?n?n genel performans?n? g?stermek |
| ?ekil 5.2 | `sekil_5_2_retrieval_strateji_karsilastirmasi.png` | Ticket-spesifik ve genel destek sorgular?n? kar??la?t?rmak |
| ?ekil 5.3 | `sekil_5_3_sorgu_gecikme_dagilimi.png` | Sorgu gecikme da??l?m?n? ve ortalama s?reyi g?stermek |
| ?ekil 5.4 | `sekil_5_4_anomali_model_kalitesi.png` | Anomaly validation metriklerini ?zetlemek |
| ?ekil 5.5 | `sekil_5_5_anomali_event_sayimlari.png` | Ground-truth, detected, matched ve hata say?lar?n? g?stermek |
| ?ekil 5.6 | `sekil_5_6_anomali_score_zaman_cizgisi.png` | Combined score de?erlerinin zamana g?re de?i?imini g?stermek |
| ?ekil 5.7 | `sekil_5_7_gun_bazli_confusion_matrix.png` | G?n bazl? do?ru/yanl?? s?n?fland?rmalar? g?stermek |
| ?ekil 5.8 | `sekil_5_8_severity_dagilimi.png` | Tespit edilen olaylar?n severity da??l?m?n? g?stermek |
| ?ekil 5.9 | `sekil_5_9_threshold_sweep.png` | Score threshold de?i?tik?e precision/recall/F1 etkisini g?stermek |

## ?izelge 5.1. Deney Veri Seti ve ?ndeks ?zeti

| ?zellik | De?er |
|---|---:|
| Retrieval de?erlendirme sorgusu | 180 |
| Ba?ar?l? retrieval sorgusu | 180 |
| Retrieval hata say?s? | 0 |
| ?ndekslenen dok?man say?s? | 34975 |
| Anomali validation ticket say?s? | 3160 |
| Embedding i?eren ticket say?s? | 3160 |
| Embedding boyutu | 384 |
| Toplam analiz penceresi | 182 |
| Evaluation ba?lang?c? | 2026-02-05T00:00:00 |
| Evaluation biti?i | 2026-07-06T23:59:59 |

## ?izelge 5.2. Retrieval Genel Metrikleri

| Metrik | De?er |
|---|---:|
| Exact Recall@5 | 0.9800 |
| Exact Recall@10 | 1.0000 |
| Exact Precision@5 | 0.1960 |
| Exact nDCG@10 | 0.9204 |
| Strategy Recall@5 | 0.8500 |
| Strategy Recall@10 | 0.9111 |
| Strategy Precision@5 | 0.2422 |
| Strategy nDCG@10 | 0.7566 |
| Category Hit@5 | 0.9611 |
| Subcategory Hit@5 | 0.8611 |
| Ortalama gecikme (sn) | 0.4684 |

## ?izelge 5.3. Retrieval Strateji Bazl? Metrikler

| Strateji | Sorgu | Recall@5 | Recall@10 | Precision@5 | nDCG@10 | Category Hit@5 | Subcategory Hit@5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Exact ticket / doc_id | 100 | 0.9800 | 1.0000 | 0.1960 | 0.9204 | 1.0000 | 1.0000 |
| Generic category/subcategory | 80 | 0.6875 | 0.8000 | 0.3000 | 0.5519 | 0.9125 | 0.6875 |

## ?izelge 5.4. Anomali Event Seviyesi Performans?

| Metrik | De?er |
|---|---:|
| Precision | 0.8605 |
| Recall | 0.9487 |
| F1 | 0.9024 |
| True Positive | 37 |
| False Positive Candidate | 6 |
| False Negative | 2 |
| Ground-truth event | 39 |
| Detected event | 43 |

## ?izelge 5.5. G?n Bazl? Anomali S?n?fland?rma Matrisi

| Ger?ek / Tahmin | Normal | Anomali |
|---|---:|---:|
| Normal g?n | 107 | 6 |
| Anomali g?n? | 2 | 37 |

Ek metrikler: accuracy=0.9474, specificity=0.9469, balanced accuracy=0.9478.

## ?izelge 5.6. Severity ve E?ik Kalibrasyonu

| Metrik | De?er |
|---|---:|
| Score threshold | 0.30 |
| Warning threshold ?nerisi | 0.40 |
| Critical threshold ?nerisi | 0.45 |
| Event severity exact match | 0.5405 |
| Positive day severity exact match | 0.5128 |
| Info event | 14 |
| Warning event | 13 |
| Critical event | 16 |

## ?izelge 5.7. API ve Demo U? Noktalar?

| Endpoint | Ama? |
|---|---|
| `/health` | Servis sa?l?k kontrol? |
| `/readiness` | Uygulaman?n haz?r olma kontrol? |
| `/api/v1/chat` | RAG tabanl? destek asistan? yan?t ?retimi |
| `/api/v1/anomaly/stats` | Drift pencereleri ve istatistikleri |
| `/api/v1/anomaly/detect` | Anomali olay listesi |
| `/api/v1/anomaly/quality` | Validation kalite metrikleri |
