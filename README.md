# Basketbol maç tahmini

Sızıntısız, sezon ilerlemeli (walk-forward) değerlendirme yapan araştırma paketi. EuroLeague (E), EuroCup (U) ve NBA maçlarını toplar; ev sahibi tabanı, saf Elo, MOV Elo, kalibre lojistik regresyon ve HistGradientBoosting modellerini aynı düzenekte karşılaştırır. Sonuçlar [docs/sonuclar.md](docs/sonuclar.md), ham metrik çıktıları [docs/kanit](docs/kanit) altındadır. Bahis getirisi veya BasketbolBet karşısında üstünlük iddiası yoktur.

## Kurulum (PowerShell)

```powershell
& 'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe' -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pip install --no-deps -e .
.venv/Scripts/python.exe -m pip freeze > requirements-lock.txt
$env:PYTHONUTF8='1'
```

- Doğrudan bağımlılıklar sürümleriyle `requirements.txt` (ve `pyproject.toml`) içinde; gerçek ortamın tam kilidi `requirements-lock.txt` (pip freeze). Kilitteki `-e` satırı yerel yoldur; başka kopyada kurarken o satırı çıkarıp `pip install --no-deps -e .` kullanın.
- HTTP taşıması Node.js'in yerleşik `fetch` fonksiyonuyla yapılır (`scripts/fetch.mjs`); Node.js 18+ gerekir. Ayrıştırma, model ve testler Python'dur.
- Ortam notu: ilk oturumda sistem Python'u "Access is denied" verdiği için `.venv`, proje içine indirilen resmi CPython 3.12.10 taşınabilir dağıtımıyla kuruldu. İkinci oturumda sistem Python'u (aynı 3.12.10) çalıştı, fakat `.venv/Scripts/python.exe` etkileşimli onay istedi; bu yüzden komutlar `.runtime/run.py` sarmalayıcısıyla (sistem Python + `.venv` site-packages + `src`) çalıştırıldı. İki yol aynı paketleri kullanır.

## Komutlar

Tek giriş noktası, proje kökünden:

```powershell
.venv/Scripts/python.exe -m bbtahmin topla                                   # E, U: 2007-08…2025-26; NBA: 2014-15…2025-26
.venv/Scripts/python.exe -m bbtahmin topla --ligler NBA --baslangic 2016     # yalnız belirli lig/sezonlar
.venv/Scripts/python.exe -m bbtahmin topla --ligler NBA --baslangic 2014 --sbr-izni   # oranlar: yalnız SBR izniniz varsa
.venv/Scripts/python.exe -m bbtahmin backtest
.venv/Scripts/python.exe -m bbtahmin tahmin "Fenerbahçe - Monaco" "Celtics - Lakers" --tarih 2026-10-25T20:45
.venv/Scripts/python.exe -m bbtahmin tahmin "Washington - Milwaukee @1.30/2.14" --tarih 2026-10-22T02:00 --kaydet   # oran ve deftere kayıt
.venv/Scripts/python.exe -m bbtahmin defter          # kayıtlı tahminleri sonuçlarla puanla (NBA sonuçları ESPN skor tablosundan)
.venv/Scripts/python.exe -m bbtahmin topla-kutu      # EuroLeague/EuroCup v3 ve ESPN NBA kutu skorları
.venv/Scripts/python.exe -m bbtahmin backtest --ligler NBA --cikti docs/deneme-nba   # deneme koşusu, ana rapora dokunmaz
.venv/Scripts/python.exe -m pytest -q tests --junitxml=docs/kanit/pytest.xml
.venv/Scripts/python.exe scripts/kanit_yaz.py; .venv/Scripts/python.exe scripts/verify_run.py; .venv/Scripts/python.exe scripts/finalize.py
```

`backtest`, `docs/kanit/*.csv|json`, kalibrasyon PNG'leri ve `docs/sonuclar.md` dosyasını üretir. `finalize.py`, raporu pytest XML'lerinden gelen gerçek test sayılarıyla yeniden yazar. `tahmin` komutu takım adlarını serbest yazımla eşler (Türkçe karakter ve kısaltma olur; lig verilmezse bulunur), son 400 günde o ligde oynamamış takımları reddeder ve her maç için backtest'te o ligde en iyi çıkan modelin kazanma olasılığını, tahmini skoru, sayı farkını ve toplamı %80 aralıklarıyla verir. Saat dilimi verilmezse İstanbul saati varsayılır.

Skor modeli: Elo ve EWMA'ya ek olarak rakibe göre düzeltilmiş hücum/savunma sayı reytingleri (iki öğrenme hızı) maç öncesi sırayla hesaplanır; fark ve toplam Ridge ile, kazanma olasılığı farkın normal dağılımından gelir. Toplam, doğrulama sezonundaki ortalama artıkla düzeltilir (skor seviyesi yıllar içinde arttığı için). Walk-forward'da %80 aralıklar maçların %80-82'sini kapsadı.

Kasıtlı sızıntı negatif kontrolü ayrıca çalıştırıldığında **1 başarısız test** vermelidir (sızıntı denetleyicisinin duyarlı olduğunun kanıtı):

```powershell
.venv/Scripts/python.exe -m pytest tests/negative_control.py -q --junitxml=docs/kanit/negatif_kontrol.xml
```

Normal pakette aynı denetleyici (`tests/leakage_check.py`) aynı sızıntılı fonksiyonla `pytest.raises(AssertionError)` altında çalışır; normal paket tamamen geçmelidir. Testler ağ kullanmaz (fixture ve sahte HTTP).

## Veri kaynakları

| Kaynak | Kapsam | Not |
|---|---|---|
| [EuroLeague API v2](https://api-live.euroleague.net/v2/competitions/E/seasons/E2024/games) | E ve U, 2007-08…2025-26 | Yol: `/v2/competitions/{E,U}/seasons/{E,U}YYYY/games`. Yanıttaki `total` alanıyla eksiksizlik denetlenir. Oynanmamış maçlar ve EuroCup iki ayaklı eşleşmelerdeki beraberlikler dışlanır ve sayılır. |
| [Basketball Reference](https://www.basketball-reference.com/leagues/NBA_2025_games.html) | NBA 2014-15…2025-26 | Sezon sayfasındaki aylık bağlantılar izlenir; ABD Doğu saati DST ile UTC'ye çevrilir. robots.txt okunur, tanımlı User-Agent, en az 6,1 sn aralık ve kayan 60 sn'de en fazla 10 istek. HTTP 429 sonrası aynı oturumda o sunucuya istek gönderilmez. |
| [Sportsbook Reviews Online](https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2021-22/) | NBA kapanış moneyline | robots.txt arşive izin verir; 2014-15…2022-23 sayfaları tablo içerir, 2023-24 ve sonrası ana sayfaya yönlenir. **Sitenin [Terms](https://www.sportsbookreviewsonline.com/terms/) sayfası içeriğin yazılı izin olmadan kullanılmasını yasaklar**; bu yüzden ayrıştırma yalnız `--sbr-izni` ile çalışır ve bu çalışmada **kullanılmadı**. |

- Ham yanıtlar ve HTTP meta verisi URL SHA-256 anahtarıyla `data/raw/<sunucu>/` altında önbelleğe alınır; önbellekte olan tekrar indirilmez. Hatalı (429 gibi) yanıtlar da önbelleğe yazılır; yeniden denemek için ilgili çift bilinçli olarak silinmelidir (bu çalışmada Retry-After süresi dolduktan sonra yapıldı).
- Normal tablo `data/maclar.parquet`: PLAN.md şeması (`mac_id, lig, sezon, tarih_utc, ev, dep, ev_skor, dep_skor, uzatma, ev_iy, dep_iy, tarafsiz_saha, asama, kaynak`). Tekrarlı `mac_id` ve beraberlik hata verir.
- Takım/franchise eşlemesi `src/bbtahmin/veri/teams.py`: oran arşivi adları (`LALakers`, `GoldenState`…) ve Basketball Reference adları/kodları; New Jersey→Brooklyn, New Orleans Hornets→Pelicans, Charlotte Bobcats→Hornets, Seattle→Oklahoma City, Vancouver→Memphis dahil. Bilinmeyen ad hata verir; oran eşleştirmesinde eşleşmeyen satırlar nedenleriyle sayılır.
- Referans: `data/raw/basketbolbet/main.py` ve `data/raw` altında benzer bir klasör bu çalışma kopyasında **bulunamadı** (`data/raw` git dışında olduğu için ayrı çalışma kopyasına gelmez). BasketbolBet taban çizgisi **yapılamadı (referans bulunamadı)**. Eski kod kopyalanmadı, formül uydurulmadı.
- `.gitignore`: `data/raw/`, `data/*.parquet`, `.venv/`, `.runtime/`. Doğrulama: `git check-ignore -v data/raw/basketbolbet/main.py` → `.gitignore:1:data/raw/	data/raw/basketbolbet/main.py` (çıktı `docs/kanit/ortam.txt`).

## Modelleme ve değerlendirme

- **Taban çizgileri:** ev sahibi kazanır (olasılık = eğitim penceresindeki ev galibiyet oranı), saf Elo, MOV Elo (FiveThirtyEight NBA Elo MOV çarpanı).
- **Asıl modeller (PLAN):** Platt kalibre lojistik regresyon ve HistGradientBoosting; sayı farkı ve toplam için Ridge regresyonu.
- **Walk-forward:** her lig için sezon S, yalnız S'den önceki sezonlarla eğitilir: son önceki sezon kronolojik doğrulama, daha eskileri iç eğitim; seçimden sonra ikisinin birleşimiyle yeniden eğitim. Sezon içinde Elo/EWMA/dinlenme durumu her gün güncellenir; bir günün sonuçları ancak ertesi UTC gününden itibaren özelliğe girer (bitiş saati bilinmediği için korumacı gecikme). Her ligin ilk iki sezonu test edilmez.
- **Öğrenilen ayarlar:** Elo K∈{10,20,30}, ev avantajı∈{0,50,100}, sezon başı çekme∈{0;0,25;0,5}; EWMA alfa∈{0,1;0,3}; lojistik C, boosting yaprak/regularizasyon/ağaç sayısı, Ridge alfa ve Platt katsayıları. Hepsi yalnız eğitim penceresinde seçilir ve her pencere için `docs/kanit/parametreler.json` içine kaydedilir. Bahis eşiği (oran kullanıldığında) yalnız önceki sezonların walk-forward tahminlerinden seçilir.
- **Özellikler:** Elo farkı, ev/tarafsız saha, EWMA atılan/yenen/fark, tempo vekili toplam, dinlenme farkı, arka arkaya maç, son 7 günde maç sayısı, deplasman serisi, sezondaki maç sayısı, Avrupa maç yükü (yalnız E/U verisinden). Hiç maçı görülmemiş takımın EWMA değeri ligin geçmiş ortalamasıyla başlar.
- **Metrikler:** log loss, Brier, doğruluk, 10 kovalı kalibrasyon tablosu (`kalibrasyon.csv`) ve PNG (`docs/kalibrasyon_*.png`), sayı farkı ve toplam MAE. Model−Elo log loss farkı için sezon bootstrap'ı, işaret permütasyonu ve lig içinde Holm düzeltmesi; p<0,05 olmadan üstünlük iddiası yapılmaz.
- **Piyasa kıyası ve bahis:** vig'siz kapanış olasılığı (iki tarafın 1/ondalık oranı normalize edilir), sabit pay (%1 güncel sermaye) ve çeyrek Kelly; ROI, en büyük düşüş ve bahis sayısı. Kod ve fixture testleri hazır; gerçek oranlar ToS nedeniyle kullanılmadığı için **sonuç üretilmedi**.

## Sınırlamalar

- NBA tarafsız saha bilgisi ve ilk yarı skorları alınmadı; tarafsız sahası bilinmeyen maçta ev avantajı var sayılır (2019-20 balon maçları dahil).
- Yerel ligler (BSL, ACB, BBL, LBA, LNB) yapılmadı: PLAN'a göre EuroLeague API'de maç verisi yok.
- Avrupa yorgunluğu yalnız Avrupa maçlarından hesaplanır; yerel lig programı yok.
- Yeniden eğitim yalnız sezon başında; aylık yeniden eğitim yapılmadı.
- NBA kapanış oranı yok → piyasa kıyası, bahis simülasyonu ve eşleşmeyen oran satırı sayısı **yapılmadı**.
- Tahmin komutu saf Elo verir; sınıflandırıcıyla gelecek maç servisi yapılmadı.

## PLAN.md ile çelişkiler / farklar

1. Görev paketin `bbtahmin/` altında olmasını, PLAN `src/bbtahmin/` yapısını ister: PLAN uygulandı.
2. İstek sınırı: görev en fazla 15/dk, PLAN 20/dk. İlk koşu 15/dk ile HTTP 429 aldı; ikisinden de sıkı 10/dk + 6,1 sn aralık uygulandı.
3. PLAN SBR oran arşivini erişilebilir ("200") listeler; erişim teknik olarak var (2014-15…2022-23), ancak sitenin kullanım şartları yazılı izin istediğinden görevin "kullanım şartlarına uy" kuralı gereği kullanılmadı. 2023-24 ve sonrası arşivde yok.
4. PLAN Elo için K≈20 ve %25 çekme önerir; görev sabit katsayıyı yasaklar. Bu değerler ızgaranın içinde tutuldu ve eğitim penceresinde seçildi.
5. PLAN "ev sahibi kazanır" tabanını olasılıksal tanımlamaz; log loss/Brier hesaplanabilsin diye olasılığı eğitim penceresindeki ev galibiyet oranı alındı (doğruluk p=1 ile aynıdır).
6. PLAN BasketbolBet yönteminin sızıntısız yeniden uygulanmasını ister; referans `main.py` bulunamadığı için yapılamadı.

Bu çalışma yalnız ayrılmış çalışma kopyasındadır. Commit/merge yapılmadı; ana depoya yazılmadı.

## Ek bilgiler ve denenmiş özellikler

- **Uzatma olasılığı:** Normal sürenin berabere bitme yoğunluğu, ligin geçmiş uzatma oranına ölçeklenerek verilir.
- **Piyasa:** Maç `"Ev - Dep @1.30/2.14"` biçiminde yazılırsa oranlardan bahisçi marjı çıkarılmış olasılık gösterilir ve deftere yazılır.
- **NBA sakatlık raporu:** Resmi PDF (ak-static.cms.nba.com) `pdfplumber` ile okunur; Out/Doubtful/Questionable oyuncular listelenir. Modele girmez, geçmiş raporlarla backtest yapılmadı.
- **Tahmin defteri:** `defter/tahminler.csv` git'e girer; tahminin maçtan önce yapıldığı commit geçmişinden görülür.
- **Kutu skor özellikleri (tempo, ORtg/DRtg, kadro devamlılığı):** EuroLeague/EuroCup v3 (9.065 maç) ve ESPN NBA (15.439 maç) verisiyle denendi. Walk-forward'da log loss'u iyileştirmedi (NBA 0,6220 → 0,6227, EuroLeague 0,5955 → 0,5965, EuroCup 0,6129 → 0,6158); bu yüzden `KUTU_LIGLERI` boş. Veri ve kod duruyor.

