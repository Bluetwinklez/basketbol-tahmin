# Ölçülen iyileştirme deneyleri

Bunlar geçmiş dönem deneyleridir. Tarihsel yayın zamanları ve sezon bütünlüğü doğrulanmış değildir. Canlı başarı artışı veya varsayılan model değişikliği anlamına gelmez. Başarısız adaylar da deney dosyalarında korunur.

## Futbol: önceki dönemde seçilen politika

Adaylar: mevcut Poisson, 90 günlük yarı ömür, 16 maçlık küçültme, rakip düzeltmesi, düşük skor düzeltmesi ve sabit karışım. Kalibrasyon önceki sezonun ilk tarih yarısında, seçim ikinci yarısında yapılır. Hedef dönemin sonuçları seçime katılmaz.

| Lig | Hedef sezon | Maç | Mevcut isabet | Önceki dönemde seçilen politika | Politika isabeti | Log loss değişimi |
|---|---|---:|---:|---|---:|---:|
| EN1 | 2025-26 | 380 | 48.68% | baseline + kalibrasyon | 48.68% | +0.00000 |
| EN2 | 2025-26 | 557 | 42.37% | baseline + kalibrasyon | 42.37% | +0.00000 |
| DE1 | 2025-26 | 306 | 51.31% | opponent_dc + kalibrasyon | 54.90% | -0.01885 |
| ES1 | 2025-26 | 380 | 52.89% | opponent_dc + kalibrasyon | 53.68% | -0.00350 |
| IT1 | 2025-26 | 380 | 49.21% | opponent_dc + kalibrasyon | 53.68% | -0.02022 |
| FR1 | 2025-26 | 305 | 51.80% | opponent + kalibrasyon | 50.16% | -0.01270 |
| NL1 | 2025-26 | 305 | 49.84% | baseline + kalibrasyon | 49.84% | +0.00938 |
| PT1 | 2025-26 | 306 | 52.94% | baseline + kalibrasyon | 52.94% | -0.00452 |
| TR1 | 2025-26 | 99 | 45.45% | baseline + kalibrasyon | 45.45% | +0.00982 |

Negatif log loss değişimi daha iyidir. İsabet ve olasılık kalitesi farklı yönlere gidebilir. Aynı hedefte en iyi görünen aday seçilip ileri başarı diye sunulmaz.

## Basketbol: ortak deney modeli ve özellik katkıları

Ortak önceki-sezon öğrenici politikası tüm liglerin mevcut üretim modeliyle aynı değildir. Bu tablo özellik katkısını karşılaştırır; üretim başarı oranını göstermez. Ev özelliğini kaldırma deneyinde Elo ev avantajı korunur.

| Lig | Sezon | Aday | Maç | Referans isabet | Aday isabet | Log loss değişimi |
|---|---|---|---:|---:|---:|---:|
| KBL | 2024-25 | form_slow | 268 | 64.18% | 63.81% | +0.00218 |
| KBL | 2024-25 | form_fast | 268 | 64.18% | 64.18% | -0.00105 |
| KBL | 2024-25 | without_rest | 268 | 64.18% | 62.31% | +0.00138 |
| KBL | 2024-25 | without_opponent_ratings | 268 | 64.18% | 64.93% | -0.00231 |
| KBL | 2024-25 | without_home | 268 | 64.18% | 64.18% | +0.00000 |
| KBL | 2025-26 | form_slow | 270 | 61.85% | 62.22% | -0.00125 |
| KBL | 2025-26 | form_fast | 270 | 61.85% | 61.85% | +0.00104 |
| KBL | 2025-26 | without_rest | 270 | 61.85% | 61.48% | -0.00050 |
| KBL | 2025-26 | without_opponent_ratings | 270 | 61.85% | 62.22% | -0.00336 |
| KBL | 2025-26 | without_home | 270 | 61.85% | 61.85% | +0.00000 |
| E | 2024-25 | form_slow | 330 | 63.94% | 63.94% | +0.00083 |
| E | 2024-25 | form_fast | 330 | 63.94% | 63.64% | -0.00020 |
| E | 2024-25 | without_rest | 330 | 63.94% | 63.94% | +0.00066 |
| E | 2024-25 | without_opponent_ratings | 330 | 63.94% | 64.55% | -0.00043 |
| E | 2024-25 | without_home | 330 | 63.94% | 63.94% | -0.00009 |
| E | 2025-26 | form_slow | 402 | 61.44% | 61.94% | -0.00139 |
| E | 2025-26 | form_fast | 402 | 61.44% | 62.19% | +0.00056 |
| E | 2025-26 | without_rest | 402 | 61.44% | 61.94% | +0.00072 |
| E | 2025-26 | without_opponent_ratings | 402 | 61.44% | 61.94% | -0.00049 |
| E | 2025-26 | without_home | 402 | 61.44% | 61.94% | -0.00016 |
| ABA | 2024-25 | form_slow | 259 | 79.92% | 80.31% | -0.00016 |
| ABA | 2024-25 | form_fast | 259 | 79.92% | 80.31% | -0.00001 |
| ABA | 2024-25 | without_rest | 259 | 79.92% | 79.54% | -0.00091 |
| ABA | 2024-25 | without_opponent_ratings | 259 | 79.92% | 79.92% | +0.00048 |
| ABA | 2024-25 | without_home | 259 | 79.92% | 79.92% | +0.00000 |
| ABA | 2025-26 | form_slow | 248 | 75.00% | 74.19% | +0.00112 |
| ABA | 2025-26 | form_fast | 248 | 75.00% | 75.00% | -0.00030 |
| ABA | 2025-26 | without_rest | 248 | 75.00% | 75.00% | +0.00033 |
| ABA | 2025-26 | without_opponent_ratings | 248 | 75.00% | 74.19% | +0.00106 |
| ABA | 2025-26 | without_home | 248 | 75.00% | 75.00% | +0.00000 |
| ECW | 2025-26 | form_slow | 214 | 69.16% | 70.09% | -0.00073 |
| ECW | 2025-26 | form_fast | 214 | 69.16% | 68.22% | +0.00243 |
| ECW | 2025-26 | without_rest | 214 | 69.16% | 68.22% | +0.00711 |
| ECW | 2025-26 | without_opponent_ratings | 214 | 69.16% | 66.82% | +0.00956 |
| ECW | 2025-26 | without_home | 214 | 69.16% | 69.16% | +0.00000 |
| FEC | 2025-26 | form_slow | 195 | 69.74% | 69.23% | -0.00012 |
| FEC | 2025-26 | form_fast | 195 | 69.74% | 69.23% | +0.00031 |
| FEC | 2025-26 | without_rest | 195 | 69.74% | 68.72% | -0.00121 |
| FEC | 2025-26 | without_opponent_ratings | 195 | 69.74% | 69.23% | +0.00217 |
| FEC | 2025-26 | without_home | 195 | 69.74% | 69.74% | +0.00000 |
| TR_BSL | 2024-25 | form_slow | 264 | 67.42% | 67.42% | +0.00000 |
| TR_BSL | 2024-25 | form_fast | 264 | 67.42% | 67.42% | +0.00000 |
| TR_BSL | 2024-25 | without_rest | 264 | 67.42% | 67.42% | +0.00000 |
| TR_BSL | 2024-25 | without_opponent_ratings | 264 | 67.42% | 67.42% | +0.00000 |
| TR_BSL | 2024-25 | without_home | 264 | 67.42% | 67.42% | +0.00000 |
| TR_BSL | 2025-26 | form_slow | 261 | 75.48% | 75.10% | -0.00201 |
| TR_BSL | 2025-26 | form_fast | 261 | 75.48% | 75.48% | -0.00100 |
| TR_BSL | 2025-26 | without_rest | 261 | 75.48% | 75.86% | -0.00302 |
| TR_BSL | 2025-26 | without_opponent_ratings | 261 | 75.48% | 74.33% | +0.00426 |
| TR_BSL | 2025-26 | without_home | 261 | 75.48% | 75.48% | +0.00000 |
| UKR | 2024-25 | form_slow | 132 | 69.70% | 70.45% | +0.00369 |
| UKR | 2024-25 | form_fast | 132 | 69.70% | 71.21% | +0.00092 |
| UKR | 2024-25 | without_rest | 132 | 69.70% | 72.73% | +0.00445 |
| UKR | 2024-25 | without_opponent_ratings | 132 | 69.70% | 69.70% | -0.00537 |
| UKR | 2024-25 | without_home | 132 | 69.70% | 69.70% | +0.00000 |
| UKR | 2025-26 | form_slow | 127 | 69.29% | 72.44% | -0.00433 |
| UKR | 2025-26 | form_fast | 127 | 69.29% | 68.50% | -0.00001 |
| UKR | 2025-26 | without_rest | 127 | 69.29% | 68.50% | -0.00057 |
| UKR | 2025-26 | without_opponent_ratings | 127 | 69.29% | 69.29% | -0.00355 |
| UKR | 2025-26 | without_home | 127 | 69.29% | 69.29% | +0.00000 |
| ARG_LNB | 2024-25 | form_slow | 429 | 64.80% | 64.80% | +0.00000 |
| ARG_LNB | 2024-25 | form_fast | 429 | 64.80% | 64.80% | +0.00000 |
| ARG_LNB | 2024-25 | without_rest | 429 | 64.80% | 64.80% | +0.00000 |
| ARG_LNB | 2024-25 | without_opponent_ratings | 429 | 64.80% | 64.80% | +0.00000 |
| ARG_LNB | 2024-25 | without_home | 429 | 64.80% | 64.80% | +0.00000 |
| ARG_LNB | 2025-26 | form_slow | 395 | 65.57% | 65.57% | +0.00000 |
| ARG_LNB | 2025-26 | form_fast | 395 | 65.57% | 65.57% | +0.00000 |
| ARG_LNB | 2025-26 | without_rest | 395 | 65.57% | 65.57% | +0.00000 |
| ARG_LNB | 2025-26 | without_opponent_ratings | 395 | 65.57% | 65.57% | +0.00000 |
| ARG_LNB | 2025-26 | without_home | 395 | 65.57% | 65.57% | +0.00000 |

## Futbol: yalnız veri değişiminin etkisi

234 yeni lisanslı finalin tamamı, aynı Poisson modeli ve aynı maçlarla karşılaştırıldı. Yeni doğrulanmış sonuçlar ve açık tarih düzeltmeleri veri değişikliğidir. Hedef UTC gününün tamamı eğitimden çıkarıldı. Tarihsel yayın erişimi bilinmediğinden bu çalışma ileri dönem başarısı değildir.

| Lig | Maç | Eski veri isabeti | Ek veri isabeti | Eski / yeni log loss |
|---|---:|---:|---:|---:|
| DE1 | 25 | 48.00% | 48.00% | 1.00894 / 1.00611 |
| EN1 | 25 | 48.00% | 44.00% | 1.01754 / 1.03222 |
| EN2 | 49 | 46.94% | 44.90% | 1.07686 / 1.07491 |
| ES1 | 25 | 48.00% | 48.00% | 0.99020 / 0.99099 |
| FR1 | 20 | 60.00% | 65.00% | 0.91080 / 0.91133 |
| IT1 | 25 | 60.00% | 60.00% | 0.94270 / 0.93059 |
| NL1 | 22 | 50.00% | 50.00% | 1.09571 / 1.09879 |
| PT1 | 13 | 61.54% | 61.54% | 0.88358 / 0.88283 |
| TR1 | 30 | 43.33% | 50.00% | 0.99820 / 0.96577 |

## Önceki dönem olasılık kalibrasyonu

8 ligde 36 karşılaştırma kaydedildi. Sıcaklık parametresi yalnız daha önceki sezonun örneklem dışı tahminlerinde seçildi; hedef sezon etiketleri seçime katılmadı. Skor ortalamaları ve aralıkları değiştirilmedi.

## Sonuç öncesi paralel kayıt

171 benzersiz maç için tahmin çifti bulunuyor. Kod/politika sürümleri ayrı deneylerdir; aynı maçın farklı sürümleri bağımsız maç gibi toplanmaz. İlk deneme sürümleri tam kaynak paketi içermediğinden yükseltme değerlendirmesine uygun değildir. Yeni sürümler kaynak kodunu, paket sürümlerini ve veri karmalarını saklar.

| Deney | Aktif | Sonuçlandı | Bekliyor | Kaynak paketi doğrulandı |
|---|---|---:|---:|---|
| 29d9f51a7ae1 | True | 0 | 149 | True |
| 3ca8c864cb8f | False | 0 | 149 | True |
| 51ffcc22a4b1 | False | 0 | 77 | False |
| 756cfe7cebbd | False | 0 | 97 | False |

## Henüz tamamlanmayan doğrulama

Bağımsız gelecek sonuçlarının birikmesi ve kalan kaynak/takvim boşluklarının giderilmesi sürüyor. Yeni model otomatik olarak yayımlanmaz. Yeterli örneklem, gün sayısı, iki zaman diliminde tutarlılık, olasılık hatası ve seçim kapsamı koşulları birlikte incelenir. Bu koşullar tamamlanmadan canlı başarı iyileşti denmez.
