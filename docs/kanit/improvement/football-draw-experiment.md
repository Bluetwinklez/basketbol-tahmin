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

## Maç dengesine göre değişen düzeltme

Antigravity'nin önerdiği maç dengesi değişkeniyle iki katsayılı bir aday da
sınandı. Ev ve deplasman galibiyet olasılıklarının mutlak farkı küçüldükçe
beraberlik düzeltmesi değişebiliyor. Katsayılar yalnız önceki sezonun ilk
bölümünde, sabit L2 cezasıyla (0,01) öğrenildi. İkinci bölümde adayın sabit
beraberlik çarpanını da geçmesi istendi.

- Aynı 3.018 maçta isabet %49,11, log loss 1,02049 ve Brier 0,61091.
  59 beraberlik seçildi, 16'sı doğru çıktı.
- Mevcut modele göre isabet farkı −0,03 yüzde puanı (%95 aralık
  [−0,40; +0,35]), log loss farkı +0,00154 (aralık [−0,00156; +0,00437]).
- Mevcut modelin galibiyet olasılıkları en fazla 15 yüzde puanı ayrışan
  1.271 maçında isabet %38,71'den %38,63'e düştü. Bu dilim yalnızca
  maç öncesi model olasılıklarıyla belirlendi.
- Dokuz ligin hiçbiri ikinci bölümde seçim koşullarını geçmedi. Aynı geçmiş
  hedef sezon yeniden kullanıldığı için iki deney de keşif niteliğindedir.

## Rakip gücünü hesaba katan model, sonraki arşiv dönemi

Sonraki sezon arşivindeki 1.052 maç (7 Ağustos–24 Kasım 2026, 74 farklı
gün) üzerinde mevcut sabit rakip gücü modelini yeniden ayarlamadan
karşılaştırdık. Her hedef ay boyunca iki model de ay başlamadan önceki
sonuçlarla eğitildi.

| Yöntem | Doğru | İsabet | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: |
| Poisson | 531 | %50,48 | 1,01045 | 0,60403 |
| Rakip gücü | 544 | %51,71 | 0,99680 | 0,59457 |

İsabet farkı +1,24 yüzde puanı, %95 gün bloklu aralık [−0,50; +3,15].
Log loss farkı −0,01365, aralık [−0,01879; −0,00846].
Brier farkı −0,00946, aralık [−0,01311; −0,00575]. İsabet için aralık
sıfırı içeriyor ve ligler arasında fark var. Bu, daha sonraki bir arşiv
karşılaştırmasıdır. Maç öncesi yayımlanmış eşli tahminlerin yerine geçmez.

`python -m scripts.evaluate_football_opponent_followup --output football-opponent-result.json`
