# Futbolda beraberlik olasılığı deneyi

2026-11-26. Dokuz ligde mevcut Poisson tahmini, sıcaklık kalibrasyonu ve yalnızca
beraberlik olasılığını çarpan aday aynı 3.018 maçta karşılaştırıldı. Ölçüm geçmiş
arşiv üzerindedir; arşivin maç günündeki yayın zamanı doğrulanmamıştır.

Her ligde 2024–25 sezonunun ilk tarih bloğunda çarpan ve sıcaklık log loss ile
seçildi. İkinci blokta çarpanın iki referansa karşı isabeti ve Brier skorunu
koruması ve log loss'u en az 0,002 azaltması istendi. Aday seçimi 2025–26
sonuçlarına bakmadan yapıldı. Model her ayın başında yalnızca daha eski maçlarla
eğitildi ve üç yöntem de aynı hedef maçlarda puanlandı.

| Yöntem | İsabet | Log loss | Brier | Beraberlik seçimi / doğru |
| --- | ---: | ---: | ---: | ---: |
| Mevcut Poisson | %49,14 | 1,01895 | 0,60980 | 1 / 0 |
| Sıcaklık | %49,14 | 1,01891 | 0,60953 | 1 / 0 |
| Beraberlik çarpanı | %49,11 | 1,02096 | 0,61135 | 46 / 12 |

Gerçekte 783 maç berabere bitti. Çarpanın isabet farkı −0,03 yüzde puanı;
eşleştirilmiş gün bloklarıyla %95 aralık [−0,37; +0,32] yüzde puanı. Log loss
farkı +0,00201, aynı yöntemle aralık [−0,00104; +0,00481]. İkinci geliştirme
bloğundaki koşulları hiçbir lig geçmedi. Bu aday canlı kullanıma alınmadı.

Tekrar üretmek için depo kökünde:

`python -m scripts.evaluate_football_draw --output football-draw-result.json`

Çıktı lig bazında veri karmalarını, seçilen çarpanları, hata ölçülerini,
beraberlik sayılarını ve eşit kapsamdaki sonuçları içerir.
