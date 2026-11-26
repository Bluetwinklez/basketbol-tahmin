# Dört basketbol liginde model harmanı

26 Kasım 2026. KBL, EuroLeague, ABA ve Türkiye BSL için skor modeli,
lojistik model ve Elo olasılıklarının logitlerini birleştiren aday sınandı.
Üç katsayı sıfırın altına inemiyor; model ayrıca ev sahibi yanlılığı için
bir sabit terim öğreniyor. Sabit 0,025 ceza, katsayıları eşit ağırlıklı
logit ortalamasına yaklaştırıyor. Katsayılar yalnız hedef sezondan önceki
üç ardışık sezonda, ilerleyen zaman testiyle üretilmiş tahminlerden
öğreniliyor. Her önceki sezona eşit ağırlık veriliyor.

| Dönem | Maç | Önceki sezonla model seçimi | Logit harmanı | Referans / aday log loss |
| --- | ---: | ---: | ---: | ---: |
| 2023–24 ila 2025–26 | 3.357 | %68,31 | %68,69 | 0,58707 / 0,58601 |
| 2026–27 (kısmi) | 365 | %64,11 | %64,38 | 0,62238 / 0,62243 |

Tam sezonlarda +13, kısmi sezonda +1 doğru. Eşleştirilmiş %95 gün bloklu
isabet aralığı tam sezonlarda [−0,30; +1,08] ve kısmi sezonda [−2,09; +2,59]
yüzde puanı. Kısmi dönemde KBL +6,49 puan, EuroLeague −2,94 puan, ABA ve
BSL eşit. Antigravity incelemesi uyarınca lig ve dönem sonuçları ayrı
raporlandı. Toplu sonuç canlı değişiklik için yeterli kanıt sağlamadı.

`python -m scripts.evaluate_basketball_logit_blend --output basketball-logit-blend.json`

Çıktı, veri karmalarını ve lig/dönem bazında beş aday veya referansı
içerir. %65 olasılık kapsamı tanısaldır ve canlı veri doğrulamasının yerini
tutmaz. Arşiv sonuçlarının maç günündeki yayın zamanı doğrulanmadı.
