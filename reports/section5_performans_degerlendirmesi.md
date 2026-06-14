# 5. PERFORMANS DEGERLENDIRMESI

Bu bolumde gelistirilen baglamsal farkindalikli BT destek asistaninin performansi iki ana eksende degerlendirilmistir. Birinci eksen, kullanici sorularina yanit uretmek icin kullanilan hibrit retrieval hattinin dogru dokumanlari ne olcude bulabildigini incelemektedir. Ikinci eksen ise destek kayitlari uzerinde calisan anomali tespit motorunun gercek anomali olaylarini yakalama, normal gunleri ayirma ve alarm onceligi uretme basarisini olcmektedir.

Performans degerlendirmesinde kullanilan sonuclar, mevcut proje veri seti, olusturulan retrieval evaluation sorgulari ve sentetik/curated anomali validation verisi uzerinden elde edilmistir. Proje kapsaminda Ozdilek kurumuna ait gercek saha verisi temin edilemedigi icin degerlendirme sonuclari dogrudan canli uretim ortami basarimi olarak degil, prototip sistemin kontrollu test ortami basarimi olarak yorumlanmalidir. Buna ragmen kullanilan test setleri, VPN kesintisi, Exchange problemi, MFA saldirisi, ransomware belirtisi, kategori kaymasi ve hacim anomalisi gibi kurumsal BT destek senaryolarini kapsayacak sekilde hazirlanmistir.

## 5.1 Degerlendirme Metrikleri

Bu calismada klasik RAGAS metriklerinden farkli olarak sistemin mevcut mimarisine uygun iki grup metrik kullanilmistir. Retrieval tarafinda Recall@k, Precision@k, nDCG@k, Category Hit@k ve Subcategory Hit@k metrikleri hesaplanmistir. Anomali tespiti tarafinda ise Precision, Recall, F1, Specificity ve Severity Match degerleri kullanilmistir. Bu metrikler hem bilgi getirme hattinin hem de anomali tespit motorunun ayri ayri incelenmesini saglamaktadir.

Asagida verilen Cizelge 5.1, degerlendirme surecinde kullanilan metrikleri, temel formullerini ve 0-1 araliginda nasil yorumlanmalari gerektigini gostermektedir.

**Buraya Cizelge 5.1 eklenecek: Olcum Metrikleri ve Aciklamalari**

| Metrik | Formul | 0-1 Arasi Anlami |
|---|---|---|
| Recall@k | \|Retrieved@k ∩ Relevant\| / \|Relevant\| | 1'e yaklastikca gerekli dokumanlarin daha fazlasi ilk k sonuc icinde bulunur. |
| Precision@k | \|Retrieved@k ∩ Relevant\| / k | 1'e yaklastikca getirilen ilk k dokumanin daha buyuk kismi gercekten ilgilidir. |
| nDCG@k | DCG@k / IDCG@k | 1'e yaklastikca dogru dokumanlar listenin daha ust siralarinda yer alir. |
| Category Hit@k | hit(expected_category, Retrieved@k) | 1'e yaklastikca sistem en az bir dogru kategori dokumanini ilk k sonuc icinde yakalar. |
| Subcategory Hit@k | hit(expected_subcategory, Retrieved@k) | 1'e yaklastikca daha dar alt kategori duzeyinde dogru sonuc yakalanir. |
| Event Precision | TP / (TP + FP) | 1'e yaklastikca uretilen anomali olaylarinin daha azi yanlis alarmdir. |
| Event Recall | TP / (TP + FN) | 1'e yaklastikca gercek anomali olaylarinin daha fazlasi yakalanir. |
| F1 | 2 x Precision x Recall / (Precision + Recall) | 1'e yaklastikca precision ve recall dengeli bicimde yuksektir. |
| Specificity | TN / (TN + FP) | 1'e yaklastikca normal gunler yanlis alarm uretilmeden normal birakilir. |
| Severity Match | dogru severity / eslesen event sayisi | 1'e yaklastikca olay onem seviyesi ground-truth ile uyumludur. |

Recall@k metrigi, sistemin ilgili dokumanlari yakalama basarisini olcmektedir. Precision@k ise getirilen dokumanlarin ne kadarinin gercekten ilgili oldugunu gosterir. nDCG@k metrigi yalnizca dogru dokumanin bulunup bulunmadigini degil, bu dokumanin siralama listesinde ne kadar ustte yer aldigini da hesaba katmaktadir. Bu nedenle nDCG, retrieval sistemlerinde siralama kalitesini yorumlamak icin onemli bir metriktir.

Anomali tarafinda precision, sistem tarafindan uretilen olaylarin ne kadarinin ground-truth ile eslestigini; recall ise ground-truth anomalilerin ne kadarinin sistem tarafindan yakalandigini gostermektedir. Specificity degeri, normal gunlerin gereksiz alarm uretilmeden normal olarak siniflandirilma basarisini ortaya koymaktadir. Severity Match ise olay tespit edildikten sonra bu olayin onem seviyesinin dogru atanip atanmadigini incelemektedir.

## 5.2 Deney Veri Seti ve Degerlendirme Kapsami

Retrieval degerlendirmesinde toplam 180 sorgu kullanilmistir. Bu sorgularin 100 tanesi belirli bir ticket kaydina yonelik exact ticket/doc_id stratejisiyle, 80 tanesi ise daha genel destek senaryolarini temsil eden category/subcategory stratejisiyle degerlendirilmistir. Indeksleme hattinda toplam 34.975 dokuman BM25 ve FAISS tarafindan aranabilir hale getirilmistir.

Anomali degerlendirmesinde 3.160 ticket iceren validation veri seti kullanilmistir. Bu kayitlarin tamaminda 384 boyutlu embedding temsilleri bulunmaktadir. Anomali motoru toplam 182 analiz penceresi uzerinde calismis, evaluation araligi 2026-02-05 ile 2026-07-06 tarihleri arasini kapsamaktadir.

**Buraya Cizelge 5.2 eklenecek: Deney Veri Seti ve Degerlendirme Kapsami**

| Ozellik | Deger |
|---|---:|
| Retrieval degerlendirme sorgusu | 180 |
| Basarili retrieval sorgusu | 180 |
| Retrieval hata sayisi | 0 |
| Indekslenen dokuman sayisi | 34.975 |
| Anomali validation ticket sayisi | 3.160 |
| Embedding iceren ticket sayisi | 3.160 |
| Embedding boyutu | 384 |
| Toplam analiz penceresi | 182 |
| Evaluation araligi | 2026-02-05 - 2026-07-06 |

Cizelge 5.2'de goruldugu gibi retrieval tarafinda tum sorgular basariyla calistirilmis ve hata sayisi 0 olarak olculmustur. Anomali tarafinda ise her ticket icin embedding temsili bulunmasi, semantic drift sinyalinin degerlendirilebilir olmasini saglamistir.

## 5.3 Retrieval Performans Sonuclari

Retrieval performansi, kullanici sorgulari icin dogru ticket veya ilgili kategori dokumanlarinin ilk siralarda getirilip getirilmedigini olcmek amaciyla degerlendirilmistir. Sistem, BM25 tabanli anahtar kelime aramasi ile FAISS tabanli embedding aramasini birlestiren hibrit bir yapi kullanmaktadir. Bu nedenle degerlendirme hem exact ID bazli hem de kategori/alt kategori bazli olarak yapilmistir.

**Buraya Cizelge 5.3 eklenecek: Retrieval Performans Sonuclari**

| Metrik | Genel Sonuc | Ticket-spesifik | Genel kategori/alt kategori |
|---|---:|---:|---:|
| Sorgu sayisi | 180 | 100 | 80 |
| Recall@5 | 0.8500 | 0.9800 | 0.6875 |
| Recall@10 | 0.9111 | 1.0000 | 0.8000 |
| Precision@5 | 0.2422 | 0.1960 | 0.3000 |
| nDCG@10 | 0.7566 | 0.9204 | 0.5519 |
| Category Hit@5 | 0.9611 | 1.0000 | 0.9125 |
| Subcategory Hit@5 | 0.8611 | 1.0000 | 0.6875 |
| Ortalama gecikme (sn) | 0.4684 | - | - |

Cizelge 5.3'te goruldugu uzere exact ticket sorgularinda Recall@5 degeri 0.9800 ve Recall@10 degeri 1.0000 olarak olculmustur. Bu sonuc, belirli bir ticket kaydina ozgu ayirt edici sorgularda sistemin beklenen dokumani ilk 5 veya ilk 10 sonuc icinde yuksek oranda bulabildigini gostermektedir. Exact nDCG@10 degerinin 0.9204 olmasi, dogru dokumanlarin yalnizca bulunmadigini, ayni zamanda siralama listesinde ust pozisyonlarda yer aldigini gostermektedir.

Genel kategori/alt kategori sorgularinda Recall@5 degeri 0.6875, Recall@10 degeri ise 0.8000 olarak hesaplanmistir. Bu sorgular, "VPN baglantisi calismiyor" veya "mail gonderemiyorum" gibi daha genel destek ifadelerini temsil ettigi icin tek bir ticket ID yerine kategori veya alt kategori duzeyinde degerlendirilmesi daha anlamlidir. Bu nedenle category-aware metrikler de rapora dahil edilmistir. Category Hit@5 degerinin 0.9611 olmasi, sistemin genel sorgularda ilk 5 sonuc icinde dogru kategoriye ait en az bir dokumani buyuk oranda yakaladigini gostermektedir. Subcategory Hit@5 degeri 0.8611 olarak olculmus ve daha dar konu basliklarinda da kabul edilebilir bir eslesme performansi elde edilmistir.

**Buraya Sekil 5.1 eklenecek: Retrieval degerlendirme metrikleri**

Sekil 5.1'de retrieval hattina ait temel metrikler gosterilmektedir. Exact Recall@5 ve Exact Recall@10 degerlerinin yuksek olmasi, ticket-spesifik sorgularda sistemin guclu oldugunu ortaya koymaktadir. Strategy Recall@5 ve Strategy Recall@10 degerleri ise genel destek sorgulari da hesaba katildiginda sistemin daha gercekci performansini temsil etmektedir. Category Hit@5 ve Subcategory Hit@5 degerleri, birebir dokuman eslesmesinin zor oldugu genel sorularda bile sistemin ilgili konu alanina yonelmeyi basardigini gostermektedir.

**Buraya Sekil 5.2 eklenecek: Retrieval stratejilerinin karsilastirilmasi**

Sekil 5.2'de exact ticket/doc_id stratejisi ile genel category/subcategory stratejisi karsilastirilmistir. Ticket-spesifik sorgularda Recall@5 ve nDCG@10 degerlerinin daha yuksek oldugu gorulmektedir. Bunun nedeni, bu sorgularin belirli bir ticket kaydini ayirt edecek sekilde hazirlanmis olmasidir. Genel kategori/alt kategori sorgularinda ise precision degeri nispeten daha yuksek, ancak recall ve nDCG degerleri daha dusuktur. Bu durum, genel kullanici sorularinda birden fazla benzer ticket kaydinin olmasi ve tek bir dogru dokuman beklentisinin daha zor hale gelmesiyle aciklanabilir.

**Buraya Sekil 5.3 eklenecek: Sorgu gecikme dagilimi**

Sekil 5.3'te sorgu gecikme dagilimi sunulmaktadir. Ortalama sorgu gecikmesi 0.4684 saniye olarak olculmustur. Bu sonuc, BM25 ve FAISS indekslerinin birlikte kullanilmasina ragmen retrieval hattinin kullanici arayuzu acisindan kabul edilebilir hizda calistigini gostermektedir. Gecikme dagiliminin buyuk bolumunun dusuk surelerde yogunlasmasi, sistemin demo ve prototip kullaniminda akici bir deneyim sundugunu desteklemektedir.

## 5.4 Anomali Tespit Performans Sonuclari

Anomali tespit motoru, destek kayitlarini zaman pencereleri halinde analiz ederek volume z-score, category divergence, semantic drift ve combined score sinyallerini hesaplamaktadir. Bu sinyaller sonucunda olusturulan eventler, ground-truth anomali olaylari ile karsilastirilmistir. Degerlendirme setinde 39 ground-truth anomaly event bulunmaktadir. Sistem bu surecte 43 event uretmis, bunlarin 37 tanesi ground-truth ile eslesmistir.

**Buraya Cizelge 5.4 eklenecek: Anomali Tespit Performans Sonuclari**

| Metrik | Deger |
|---|---:|
| Ground-truth event | 39 |
| Detected event | 43 |
| Matched event / True Positive | 37 |
| False positive candidate | 6 |
| False negative | 2 |
| Event Precision | 0.8605 |
| Event Recall | 0.9487 |
| Event F1 | 0.9024 |
| Gun bazli specificity | 0.9469 |
| Gun bazli accuracy | 0.9474 |
| Gun bazli balanced accuracy | 0.9478 |
| Severity exact match | 0.5405 |
| Score threshold | 0.30 |
| Warning / Critical esik onerisi | 0.40 / 0.45 |

Cizelge 5.4'te goruldugu uzere event precision degeri 0.8605, event recall degeri 0.9487 ve event F1 degeri 0.9024 olarak hesaplanmistir. Bu sonuc, sistemin anomali olaylarini yakalama konusunda yuksek recall elde ettigini ve uretilen alarmlarin buyuk bolumunun ground-truth ile eslestigini gostermektedir. False positive candidate sayisinin 6 olmasi, sistemin bazi gunlerde ground-truth tarafindan etiketlenmemis ancak skor olarak supheli bulunan olaylar urettigini gostermektedir. Bu olaylar dogrudan kesin yanlis alarm olarak degil, "inceleme adayi" olarak yorumlanmistir.

Gun bazli specificity degeri 0.9469 olarak olculmustur. Bu deger, normal olarak etiketlenen gunlerin buyuk bolumunun sistem tarafindan da normal olarak siniflandirildigini gostermektedir. Bu metrik operasyonel acidan onemlidir; cunku anomali tespit sistemlerinde yalnizca anomalileri yakalamak degil, normal gunlerde gereksiz alarm uretmemek de kritik bir basari kriteridir.

Severity exact match degeri 0.5405 olarak hesaplanmistir. Bu sonuc, sistemin olay tespitinde basarili olmakla birlikte olay onem seviyesini tam olarak atama konusunda gelistirmeye acik oldugunu gostermektedir. Diger bir ifadeyle sistem "anomali var mi?" sorusuna yuksek basariyla cevap verirken, "bu anomali info, warning veya critical seviyesinde mi?" sorusunda daha orta seviyede performans gostermektedir.

**Buraya Sekil 5.4 eklenecek: Anomali tespit modeli kalite metrikleri**

Sekil 5.4'te anomali tespit modelinin event precision, event recall, event F1, day F1, specificity ve severity match metrikleri birlikte gosterilmistir. Event recall degerinin %95 seviyesinde olmasi, ground-truth anomalilerin buyuk bolumunun yakalandigini gostermektedir. Event precision ve F1 degerleri de sistemin dengeli bir alarm uretim performansina sahip oldugunu ortaya koymaktadir. Buna karsilik severity match degerinin diger metriklere gore daha dusuk kalmasi, severity kalibrasyonunun gelecek calismalarda iyilestirilmesi gereken bir nokta oldugunu gostermektedir.

**Buraya Sekil 5.5 eklenecek: Gun bazli confusion matrix**

Sekil 5.5'te gun bazli confusion matrix sunulmaktadir. Buna gore 107 normal gun dogru sekilde normal olarak siniflandirilmis, 37 anomalili gun ise dogru sekilde anomali olarak yakalanmistir. 6 normal gun false positive candidate olarak isaretlenmis, 2 anomalili gun ise kacirilmistir. Bu dagilim, sistemin hem anomalileri yakalama hem de normal gunleri koruma acisindan dengeli bir davranis sergiledigini gostermektedir.

## 5.5 Esik Degeri ve Kalibrasyon Analizi

Anomali tespit sistemlerinde combined score icin secilen esik degeri, precision ve recall arasindaki dengeyi dogrudan etkilemektedir. Daha dusuk esik degerleri daha fazla anomali adayinin yakalanmasini saglarken false positive sayisini artirabilir. Daha yuksek esik degerleri ise false positive sayisini azaltabilir; ancak bu durumda bazi gercek anomaliler kacirilebilir.

Bu calismada gun bazli degerlendirme icin score threshold degeri 0.30 olarak kullanilmistir. Warning ve critical severity seviyeleri icin validation sonucunda onerilen esik degerleri sirasiyla 0.40 ve 0.45 olarak hesaplanmistir. Bu esikler, sistemin review candidate, warning alert ve critical alert ayrimini daha tutarli yapabilmesi icin kullanilmistir.

**Buraya Sekil 5.6 eklenecek: Anomali esik degeri duyarlilik analizi**

Sekil 5.6'da threshold degeri degistikce precision, recall ve F1 skorlarinin nasil degistigi gosterilmektedir. Dusuk threshold degerlerinde recall yuksek kalmakta, ancak false positive sayisinin artmasi nedeniyle precision dusmektedir. Threshold yukseldikce precision artmakta fakat recall azalma egilimi gostermektedir. Secilen 0.30 esik degeri, F1 ve balanced accuracy acisindan dengeli bir nokta olarak degerlendirilmistir.

## 5.6 Genel Degerlendirme

Elde edilen sonuclar, gelistirilen sistemin iki ana bilesende de islevsel bir prototip olusturdugunu gostermektedir. Retrieval tarafinda 34.975 dokuman uzerinde calisan hibrit BM25 + FAISS yapisi, ticket-spesifik sorgularda yuksek exact recall ve nDCG degerleri elde etmistir. Genel destek sorgularinda ise kategori ve alt kategori bazli metrikler, sistemin kullanici sorusunu dogru konu alanina yonlendirme konusunda basarili oldugunu gostermektedir.

Anomali tespiti tarafinda event precision, recall ve F1 degerleri yuksek seviyededir. Gun bazli specificity ve accuracy degerleri, sistemin normal gunlerde gereksiz alarm uretme egiliminin sinirli oldugunu gostermektedir. Bununla birlikte severity exact match degerinin diger metriklere gore daha dusuk olmasi, alarm onceliklendirme tarafinda daha fazla kalibrasyon yapilmasi gerektigini ortaya koymaktadir.

Bu bolumde sunulan performans degerlendirmesi, sistemin mevcut veri kosullari altinda calisir, olculebilir ve savunulabilir bir prototip oldugunu gostermektedir. Gercek kurum verisi ile yeniden egitim ve saha validasyonu yapildiginda retrieval sorgularinin cesitlendirilmesi, severity esiklerinin yeniden ayarlanmasi ve anomali etiketlerinin uzman geri bildirimiyle zenginlestirilmesi sistemin daha guvenilir hale gelmesini saglayacaktir.
