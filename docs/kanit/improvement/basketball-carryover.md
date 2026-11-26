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
