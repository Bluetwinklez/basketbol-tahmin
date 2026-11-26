# Geçerli maç öncesi kanıt

29 Ekim 2026: Bu klasör temel basketbol modellerinin tek güncel kanıt kaynağıdır.
`manifest.json` model değerlendirme tarihini korur; `derived_reports` ise bu
tahminlerden türetilen raporların tarihini ve yerel oran dosyasının hash'ini tutar.
Bu güncellemede model yeniden eğitilmedi ve yeni bir özellik alınmadı.

`metrikler.csv`, `parametreler.json` ve sıkıştırılmış `tahminler.csv.gz`
22 Ekim tarihli sızıntısız koşudan gelir. Maç sonrası katılım özellikleri kapalıdır.
`toplam.csv` kısmi sezonu da içerir; README'nin tamamlanmış sezon tablosu
`completed_seasons.csv` ve `confidence.csv` ile kontrol edilir.

Piyasa raporu aynı imzalı tahminlerin yerel SBR oranlarıyla kesişimidir.
`piyasa.csv` tüm eşleşen sezonları; `piyasa_ozet.csv` ise hem harmanın hem
tabanların bulunduğu ortak sezonu içerir: 2022-23, 664 maç. Bu sayı tüm sezon
kapsamı değildir. Harmanın ilk eğitim sezonu 2021-22'dir. Bu dar kıyas,
PR #30'daki 2017-18–2022-23 / 6.758 maçlık ayrı koşunun yerine geçmez;
iki kohortun sonuçları karşılaştırılamaz. Tarihsel koşunun özetleri üst
`docs/kanit/` klasöründe korunur ve güncel kanıt olarak kullanılmaz.

`bahis.csv` her yöntem ve sezonun sonucunu ayrı tutar. Tek sezonluk sonuçtan
kârlılık veya piyasayı geçme iddiası çıkarılmaz. `harman.json` tüm eşleşen
sezonlarla ileri tarihli araştırma gösterimi için öğrenilir; geçmiş performansı
ölçen harman satırları yalnız önceki sezonlarla eğitilir.

Yeniden üretim (proje kökünde, yerel oran dosyası gerektiğinde):

```powershell
& C:/Tools/bbtahmin-venv/Scripts/python.exe -X utf8 -m bbtahmin backtest --ilk-test 2021 --cikti docs/kanit/pregame_verified
& C:/Tools/bbtahmin-venv/Scripts/python.exe -X utf8 scripts/refresh_verified_evidence.py
```

Yalnız türetilen raporları yenilemek için ikinci komut yeterlidir; tahminlerin
önce mevcut imzayla eşleşmesi gerekir. Ham SBR oranları git dışında kalır.
Dağıtımda CSV sıkıştırılırsa yenileme komutu `tahminler.csv.gz` dosyasını da
manifest'e ekler. Kaynak tahminler, metrikler, oran özeti veya katsayılar
değiştirilirse doğrulama başarısız olur; varsayılan harman gösterilmez.

Diğer araştırma kohortları (`runtime_validation`, `calibration_research` vb.)
kendi manifest ve kapsamlarıyla ayrı araştırmalardır. Eski `docs/sonuclar.md`
ve üst `docs/kanit/metrikler.csv` sızıntılı tarihsel çıktılardır.
