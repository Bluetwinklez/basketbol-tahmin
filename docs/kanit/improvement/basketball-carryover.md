# Basketbol Elo: sezon başında takım gücü ne kadar korunsun?

26 Kasım 2026. KBL, EuroLeague, ABA ve Türkiye BSL arşivinde Elo'nun
sezon geçişinde 1500'e doğru küçültülme oranı incelendi. Mevcut değer
0,25. Adaylar 0,05, 0,20, 0,35, 0,50 ve 0,70. Karar için yalnızca
önceki üç ardışık sezonun arşivdeki ilk 45 günlük maçları kullanıldı.
Bir oran, üç sezonun en az ikisinde log loss'u düşürmeli, ortalama
log loss'u en az 0,002 iyileştirmeli ve ortalama isabeti korumalıydı.
Aksi durumda referans oran korundu. Aynı UTC gününün sonuçları o
günün maçlarını puanlarken kullanılmadı.

| Dönem | Maç | Referans isabeti | Seçilen oranla isabet | Log loss farkı |
| --- | ---: | ---: | ---: | ---: |
| 2023–24 ila 2025–26, ilk 45 gün | 815 | %66,50 | %66,75 | +0,00043 |
| 2023–24 ila 2025–26, tüm maçlar | 3.357 | %68,13 | %68,31 | +0,00005 |
| 2026–27, ilk 45 gün | 296 | %64,19 | %65,20 | −0,00653 |
| 2026–27, kısmi sezon | 369 | %63,96 | %64,77 | −0,00617 |

Son dönemde 3 ek doğru var. Kısmi sezonun %95 gün bloklu isabet farkı
aralığı [−0,55; +2,25] yüzde puanı. Sezon başında ABA iyileşti, KBL
geriledi. Antigravity'nin önerisiyle en az bir takımın önceki sezon
arşivinde görünmediği maçlar ayrıca raporlandı. Son dönemde bu grupta
26/40 yerine 29/40 doğru görüldü; tam sezonlarda fark sıfırdı (92/136).
Yeni takımların 1500'den başladığı ve aynı günkü sonuçları görmediği
sentetik testle doğrulandı. Bu geçmiş arşiv deneyi üretim değişikliği
için yeterli kanıt sağlamadı.

`python -m scripts.evaluate_basketball_carryover --output basketball-carryover.json`

## ABA'da 0,05 oranının ayrı arşiv kontrolü

Kısmi 2026–27 sezonunda seçilmiş olan 0,05 oranı sabit tutuldu ve
2017–18 ila 2025–26 arasındaki dokuz arşiv sezonunda 0,25 ile
karşılaştırıldı. İlk altı sezon, kısmi 2026–27 seçiminin kullandığı üç
sezondan ayrı raporlandı. Antigravity'nin önerdiği sezon bazında
tekrarlanabilirlik kontrolü uygulandı. Maç başına skorlar sadece
önceki UTC günlerindeki sonuçlarla oluşturuldu.

| Dönem | Maç | 0,25 isabeti | 0,05 isabeti | 0,25 / 0,05 log loss |
| --- | ---: | ---: | ---: | ---: |
| 2017–18 ila 2022–23 | 975 | %73,33 | %72,92 | 0,54646 / 0,53823 |
| 2023–24 ila 2025–26 (seçimde kullanılan) | 705 | %75,46 | %74,61 | 0,51584 / 0,50645 |
| Önceki dokuz sezon | 1.680 | %74,23 | %73,63 | 0,53361 / 0,52489 |
| Önceki dokuz sezon, ilk 45 gün | 407 | %72,48 | %72,73 | 0,55747 / 0,54842 |
| 2026–27 (kısmi, hipotezin kaynağı) | 80 | %67,50 | %72,50 | 0,56291 / 0,54193 |

0,05 dokuz sezonun sekizinde log loss'u düşürdü. Önceki 1.680 maçta
log loss farkı −0,00872 (%95 gün bloklu aralık [−0,01346; −0,00373]),
ancak aday 10 daha az doğru tahmin yaptı. İlk 45 günde bir ek doğru
vardı; isabet farkının aralığı [−1,67; +2,18] yüzde puanı.
Kısmi sezondaki dört ek doğru eski dönemlerde tekrarlanmadı. Bu tarihsel
bulgu olasılıkları araştırmaya değer kılıyor, fakat isabet hedefi için
canlı modele geçişi desteklemiyor.

`python -m scripts.evaluate_basketball_carryover --aba-replication --output aba-replication.json`
