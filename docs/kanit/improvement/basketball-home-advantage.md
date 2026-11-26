# Basketbolda ev sahibi Elo avantajı

26 Kasım 2026. KBL, EuroLeague, ABA ve Türkiye BSL için ev sahibi
avantajının 50 Elo puanından farklı olması sınandı. Adaylar 0, 25, 50,
75 ve 100. Her ligde seçim yalnız önceki iki sezonun tarafsız olmayan
maçlarına dayanıyor. Aday, ortalama isabeti en az 0,25 yüzde puanı
artırmalı, log loss'u en az 0,001 düşürmeli, Brier'ı kötüleştirmemeli
ve iki sezonun hiçbirinde log loss'u 0,003'ten fazla artırmamalıydı.

İki ayrı deney, tahmin anındaki avantajı takım reytinglerine etkisinden
ayırıyor. İlkinde bütün yöntemler aynı tarihsel Elo puanlarını
kullanıyor; yalnız tahmin formülündeki ev sahibi avantajı değişiyor.
Antigravity incelemesinde önerilen ikinci deneyde, her adayın Elo
puanları o adayın avantajıyla ayrı güncelleniyor. Her iki durumda da
sonuçlar aynı UTC gününün tahminlerinden sonra reytinge yansıyor.

| Arşiv dönemi | Maç | Referans isabeti | Yalnız tahminde değişiklik | Reyting güncellemesinde de değişiklik |
| --- | ---: | ---: | ---: | ---: |
| 2023–24 ila 2025–26 | 3.357 | %68,13 | %67,98 | %67,80 |
| 2026–27 (kısmi) | 369 | %63,96 | %62,33 | %63,41 |

Tam sezonlarda log loss farkı sırasıyla −0,00261 ve −0,00275.
Kısmi sezonda farklar +0,00936 ve +0,00709 ile tersine döndü.
Dört isabet farkının da %95 gün bloklu güven aralığı sıfırı
içeriyor. Arşivdeki 11 tarafsız maçta, yalnız tahmin formülü
değiştirildiğinde olasılıklar eşitti. Reyting güncellemeleri de
değiştiğinde log loss küçük bir fark gösterdi (+0,00102). Bu,
önceki ev maçlarının tarafsız maçlara taşınabilen dolaylı etkisini
gösteriyor; örneklem küçük. Canlı ayarı değiştirmek için yeterli
kanıt yok. Arşiv verilerinin maç günündeki yayın zamanı doğrulanmadı.

`python -m scripts.evaluate_basketball_home_advantage --output home-advantage.json`

`python -m scripts.evaluate_basketball_home_advantage --update-ratings --output home-advantage-updated.json`
