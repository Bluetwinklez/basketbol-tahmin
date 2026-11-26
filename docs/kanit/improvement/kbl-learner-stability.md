# KBL model seçiminin sezonlar arası karşılaştırması

26 Kasım 2026. KBL'nin aynı arşiv maçlarında, önceki sezonun ikinci
bölümünde en düşük log loss veren modeli seçen mevcut kural, üç modelin
eşit ortalaması ve üç önceki sezonda öğrenilen ağırlıklı ortalama ile
karşılaştırıldı. Skor, lojistik ve Elo ayrı ayrı ve ev sahibi kuralı da
sonuçta yer alır.

Ağırlıklar yalnızca hedef sezondan önceki üç ardışık sezonda, her
sezonun kendi ilerleyen zaman testiyle üretilen olasılıklardan öğrenildi.
Her sezona eşit ağırlık verildi. Sabit 0,03 L2 cezası karışımı eşit
ağırlıklara yaklaştırır. Aynı UTC gününün maçları takım özellikleri için
birbirinin sonucunu görmez. Arşiv yayın zamanları doğrulanmadı.

| Dönem | Yöntem | Maç | İsabet | Log loss | Brier | Olasılık ≥ %65 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2022–23 ila 2025–26 | Mevcut seçim | 1.077 | %63,97 | 0,64830 | 0,45633 | %34,73 |
| Aynı | Eşit ortalama | 1.077 | %62,21 | 0,64720 | 0,45504 | %33,43 |
| Aynı | Üç sezonlu ortalama | 1.077 | %62,02 | 0,64655 | 0,45449 | %34,91 |
| 2026–27 (kısmi) | Mevcut seçim (Elo) | 77 | %55,84 | 0,68465 | 0,49111 | %27,27 |
| Aynı | Eşit ortalama | 77 | %61,04 | 0,67674 | 0,48370 | %14,29 |
| Aynı | Üç sezonlu ortalama | 77 | %62,34 | 0,67717 | 0,48405 | %12,99 |

Üç sezonlu ortalama son 77 maçta 48 doğru yaptı, referans 43 doğru
yaptı. İsabet farkı +6,49 yüzde puanı (%95 gün bloklu aralık [0,00; +14,12]).
Dört tamamlanmış sezonda fark −1,95 puan (aralık [−3,62; −0,28]).
Son dönemde log loss farkının aralığı sıfırı içeriyor. Basit ev sahibi
seçimi aynı 77 maçta 45 doğru yaptı. Kazanma olasılığı eşiği yalnızca
karşılaştırma amaçlıdır, canlı veri ve skor tutarlılığı kontrollerini
içermez. Bu sonuçlar KBL modelini yükseltme koşullarını karşılamıyor.

`python -m scripts.evaluate_kbl_learner_stability --output kbl-stability.json`

Çıktı veri karmasını, sezon başına ağırlıkları, eşit ortalamaya göre
log loss farklarını, eşleştirilmiş belirsizlik aralıklarını ve eşit
kapsam karşılaştırmalarını kaydeder.
