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

## Beklenen gol toplamıyla beraberlik düzeltmesi

Antigravity'nin önerisiyle maç öncesi beklenen gol toplamı da modele
eklendi. Düzeltme önceki sezonun ilk bölümünde öğrenildi ve ikinci bölümde
Poisson, sıcaklık, sabit çarpan ve maç dengesi adaylarıyla karşılaştırıldı.
Her iki sezonda da dokuz ligin hiçbiri seçim koşulunu geçmedi.

| Arşiv dönemi | Maç | Poisson isabeti | Yeni aday | Poisson / aday log loss |
| --- | ---: | ---: | ---: | ---: |
| 2025–26 | 3.018 | %49,14 | %49,07 | 1,01895 / 1,02107 |
| 2026–27 (kısmi) | 1.052 | %50,48 | %50,57 | 1,01045 / 1,01278 |

Dengeli ve beklenen toplamı 2,5'in altındaki maçlarda beraberlik Brier
skoru her iki dönemde de kötüleşti (0,2085 → 0,2107 ve 0,2041 → 0,2049).
Bu dilim Poisson'un maç öncesi galibiyet olasılığı farkı en fazla 0,15
olan maçlardan oluşuyor. 2026–27 için şu komut aynı protokolü yeniden çalıştırır:

`python -m scripts.evaluate_football_draw --development 2025-26 --target 2026-27 --output football-draw-2026.json`

## Mevcut gölge politikasına karşı rakip gücü

2026–27 arşivindeki aynı 1.052 maçta gölge politikası lig başına kayıtlı
algoritma ve sıcaklıkla tekrar oynatıldı. Algoritmalar ay başında, o aydan
önceki verilerle eğitildi. Bu arşiv tekrarı, canlı koşudaki kaynak kontrollerini
ve maç öncesi yayımlama koşulunu kanıtlamaz.

| Yöntem | İsabet | Log loss | Brier | %65 eşiği ve model geçmişi koşulunu geçenler |
| --- | ---: | ---: | ---: | ---: |
| Gölge politikası | %51,05 | 0,99769 | 0,59543 | %10,08 |
| Sabit rakip gücü | %51,71 | 0,99680 | 0,59457 | %5,23 |

Sabit rakip gücünün isabet farkı +0,67 yüzde puanı (gün bloklu %95 aralık
[−0,26; +1,70]). İlk dönemde −0,23, ikinci dönemde +1,28 yüzde puanı.
Log loss farkının aralığı da sıfırı içeriyor [−0,00755; +0,00686].
Bu bulgularla mevcut gölge politikasını değiştirmek için yeterli kanıt yok.
