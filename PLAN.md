# Basketbol Tahmin — Tasarım

Amaç: [ugurakami/BasketbolBet](https://github.com/ugurakami/BasketbolBet)'ten ölçülebilir biçimde daha iyi bir maç tahmin sistemi. "Daha iyi", geriye dönük testte (walk-forward) daha düşük log loss ve Brier skoru demektir; mümkün olan liglerde bahis piyasasının kapanış oranlarıyla karşılaştırılır.

## BasketbolBet'in sorunları (neden yeniden yazıyoruz)

1. **Veri sızıntısı:** Doğruluk, test edilen maçların sonuçlarını da içeren takım istatistikleriyle ölçülüyor (`analyze_prediction_accuracy_detailed`). Gösterilen doğruluk şişkin.
2. **Elle ayarlanmış katsayılar:** `guc_farki * 0.6`, ev avantajı 3.2 gibi sayılar veriden öğrenilmiyor ve doğrulanmıyor.
3. **Olasılık kalibre değil:** `50 + ...` formülü olasılık değil; %8–92 sınırı yapay.
4. **Veri elle giriliyor:** Tek sezonluk 2.470 satırlık TSV; geçmiş sezon yok, oran yok.
5. **Rakip gücü döngüsel:** Güç puanı tüm sezonun maçlarından hesaplanıyor, sonra aynı maçlara uygulanıyor.
6. **Basketbolda beraberlik yok** ama kod "Berabere" durumunu ele alıyor (uzatma skorları yanlış girilmiş olabilir).
7. **Piyasa ile kıyas yok:** Model bahis oranlarından iyi mi kötü mü, bilinmiyor.

## Veri kaynakları (2026-10-21'de bu makineden doğrulandı)

| Lig | Kaynak | Durum |
|---|---|---|
| EuroLeague (`E`), EuroCup (`U`) | `https://api-live.euroleague.net/v2/competitions/{E,U}/seasons/{E2024}/games` (resmi, ücretsiz, anahtarsız) | 200, ~2000'den bu yana sezonlar |
| NBA skorları | `https://www.basketball-reference.com/leagues/NBA_2025_games.html` (aylık sayfalar; en fazla 20 istek/dk) | 200 |
| NBA kapanış oranları | `https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-YYYY-YY/` | 200 (arşiv sezonları) |
| Türkiye BSL, İspanya ACB, Almanya BBL, İtalya LBA, Fransa LNB | EuroLeague API'de listeleniyor ama maç verisi **yok** | Kaynak araştırılacak |
| stats.nba.com | Zaman aşımı | Kullanılmayacak |

## Mimari

```
basketbol-tahmin/
  src/bbtahmin/
    veri/        # toplayıcılar: euroleague.py, nba_bref.py, nba_odds.py, (yerel ligler)
    ozellik.py   # yalnızca maç öncesi bilgiden özellik üretimi
    elo.py       # MOV'lu Elo, lig başına ev avantajı, sezon başı ortalamaya çekme
    model.py     # olasılık (lojistik / gradient boosting), fark ve toplam skor regresyonu
    backtest.py  # walk-forward değerlendirme, metrikler, bahis simülasyonu
    tahmin.py    # gelecek maçlar için tahmin + rapor
  data/raw/      # ham indirmeler (git'e girmez)
  data/maclar.parquet  # normalleştirilmiş tek tablo
  tests/
```

### Normalleştirilmiş maç tablosu

`mac_id, lig, sezon, tarih_utc, ev, dep, ev_skor, dep_skor, uzatma (bool), ev_iy, dep_iy, tarafsiz_saha (bool), asama (normal/playoff/final-four), kaynak`

Takım adları kaynak koduyla tutulur (`ULK` gibi); görünen ad ayrı eşleme tablosunda.

### Özellikler (hepsi maç saatinden ÖNCEKİ verilerden)

- Elo farkı (FiveThirtyEight NBA Elo yaklaşımı: K≈20, MOV çarpanı, sezon başında ortalamaya %25 çekme), lig bazında öğrenilen ev avantajı
- Üstel ağırlıklı (EWMA) atılan/yenen sayı, sayı farkı; tempo vekili olarak toplam skor
- Dinlenme günü, arka arkaya maç (back-to-back), son 7 günde maç sayısı, deplasman serisi
- EuroLeague/EuroCup oynayan takımlarda hafta içi Avrupa maçı yorgunluğu
- Sezondaki maç sayısı (erken sezonda belirsizlik)

### Modeller

1. **Taban çizgileri:** "ev sahibi kazanır", saf Elo. Her yeni model bunları geçmek zorunda.
2. Kazanma olasılığı: lojistik regresyon ve LightGBM/HistGradientBoosting; izotonik ya da Platt kalibrasyonu yalnızca eğitim penceresinde.
3. Sayı farkı ve toplam skor: regresyon; normal dağılım varsayımıyla handikap ve alt/üst olasılığı.

### Değerlendirme (sızıntı olmamalı)

- Walk-forward: sezon S'yi tahmin ederken yalnızca S'den önceki sezonlar ve S içindeki o tarihten önceki maçlar kullanılır. Modeller sezon başında (ve isteğe bağlı aylık) yeniden eğitilir.
- Metrikler: log loss, Brier, doğruluk, kalibrasyon tablosu (10 kova), fark için MAE.
- NBA'de piyasa kıyası: kapanış oranlarından vig'siz olasılık → aynı metrikler. Bahis simülasyonu yalnızca modelin piyasaya göre avantajı ≥ eşik olduğunda, sabit pay ve çeyrek Kelly; ROI ve en büyük düşüş raporlanır.
- BasketbolBet'in kendi yöntemi de aynı walk-forward düzeneğinde yeniden uygulanıp karşılaştırılır (sızıntısız hâli).

## Gerçekçi beklenti

NBA'de iyi modeller maçların ~%66–68'ini bilir; kapanış oranları ~%68–70 civarındadır. Piyasayı uzun vadede geçmek çok zordur; amaç önce dürüst ölçüm, sonra piyasaya yakın kalibrasyondur. Avrupa liglerinde veri az ve piyasa daha az verimli olabilir.
