English: [README.md](README.md)

# Basketbol ve Futbol Maç Önü Araştırması

Maç önü basketbol ve futbol olasılıkları, skor/gol farkları ve toplamları için bir Python araştırma paketi (`bbtahmin`). Tekrarlanabilir tarihsel arşivleri, kronolojik ileri yürüyüş (walk-forward) değerlendirmesini, deneysel bir İddaa bülten okuyucusunu, yerel bir tarayıcı uygulamasını ve salt okunur bir yerel MCP sunucusunu bir araya getirir.

## Kapsam: ligler ve modeller

- **Çekirdek basketbol (54,808 kayıtlı maç; ayrı Asya arşivleri 12,850 sonuç içerir):** NBA, EuroLeague (`E`), EuroCup (`U`) ve Avustralya NBL. Modeller: ev sahibi tabanı, Elo, MOV Elo, lojistik regresyon, gradyan artırma, skor regresyonu ve topluluk (ensemble); önceki sezon parametre/model seçimi ve lig bazında genişletilmiş özellik seçimiyle kronolojik olarak değerlendirilir. Geriye dönük oyuncu yokluğu özellikleri ve dört faktör/şut profilleri varsayılan olarak kapalıdır.
- **Ek basketbol arşivleri (ayrı modeller):** Çin CBA (2,386 maç, ayrıca deneysel elle girilen normal süre canlı durum projeksiyonu), EuroCup Women (`ECW`, 678), FIBA Europe Cup erkekler (`FEC`, 651), VTB erkekler (860), ABA League büyük erkekler (3,023), Türkiye BSL (2,523), Ukrayna SuperLeague (997), Arjantin Liga Nacional (`ARG_LNB`) ve Asya arşivleri (12,850 farklı nihai maç: KBL 2,549, Japonya B1 5,644, Japonya B2 3,769, PBA Governors Cup 322, Commissioners Cup 291, Philippine Cup 275).
- **Futbol (ayrı iş akışı):** 17 Avrupa liginde (Türkiye Süper Lig dahil) 62,373 kayıtlı topluluk kaynağı nihai maçı, ayrıca istenen ligler için ayrı tarihsel arşivler. Normal süre 1/X/2, gol toplamları ve karşılıklı gol olasılıklarını tahmin eder; rakibe göre düzeltilmiş (opponent-adjusted) model varsayılandır (`--model baseline` ve `ensemble` hâlâ kullanılabilir).
- **Açık sınırlar:** Japonya 2026–27 B.PREMIER/B.ONE için eski model aktarımı ayrıca doğrulanana kadar engellidir; desteklenmeyen liglerde (ör. İsveç SBL) etkinleştirilmiş model yoktur; bahis oynama ve getiri garantisi sunulmaz. Güncel teslimat denetimi ve çözülmemiş kabul ölçütleri: [kapsam defteri](docs/delivery-scope.md) (ayrıca bkz. [docs/screenshot-leagues.md](docs/screenshot-leagues.md)). Ekran görüntüsü eşleşmeleri, bilinmeyen tarihler ve kaynak doğrulaması model performansından ayrı izlenir.

## Dürüst performans özeti

**Daha fazla veri, tahmin doğruluğunda genel bir artış kanıtlamamıştır.** Aşağıdaki tüm sayılar geriye dönük kronolojik backtest sonuçlarıdır; canlı sonuç veya bahis garantisi değildir. İleriye dönük futbol ve yakın dönem genişleme kohortları hâlâ beklemede ya da genel doğruluğu doğrulamak için fazla küçüktür.

Son beş tamamlanmış çekirdek basketbol sezonunda (**2021–22'den 2025–26'ya**, fiili katılımcı yokluğu etiketleri hariç; [docs/kanit/pregame_verified](docs/kanit/pregame_verified)) sabit model sonuçları:

| Lig | Model | Maç | Kazanan doğruluğu | Log loss |
|---|---|---:|---:|---:|
| NBA | Score regression | 6,605 | 65.80% | 0.61977 |
| EuroLeague | Score regression | 1,690 | 64.62% | 0.61594 |
| EuroCup | Score regression | 970 | 65.88% | 0.60567 |
| NBL | Ensemble | 824 | 61.04% | 0.65857 |

- **Güven filtresi ve tam kapsam:** aynı 6,605 NBA maçında, öngörülen kazanan olasılığı ≥70% olanları filtrelemek 1,684 maçta 79.69% doğruluk verir (25.50% kapsam; [confidence.csv](docs/kanit/pregame_verified/confidence.csv)). Bu bir alt küme tanısıdır, genel doğruluk değildir.
- **Ekim 2026 doğruluk incelemesi:** lig bazında genişletilmiş basketbol özellikleri küçük kazanımlar sağladı (ör. NBA 65.78% → 66.03%), rakibe göre düzeltilmiş futbol modelini varsayılan yapmak ise 17 ligde 3,973 maçlık aynı 2025–26 kohortunda 1/X/2 doğruluğunu 47.80%'den 49.18%'e çıkardı ([docs/accuracy-review.md](docs/accuracy-review.md)).
- **NBA kapanış oranları:** Eşleşen 6,758 maçta (2017–18'den 2022–23'e), komisyonsuz (no-vig) piyasa skor modelini geride bıraktı. Önceki sezonlara uydurulan harman piyasaya yakın kaldı. Bkz. [piyasa karşılaştırması](docs/kanit/piyasa.csv) ve [bahis simülasyonu](docs/kanit/bahis.csv).
- **CLI'da NBA oranları:** `Piyasa` (komisyonsuz piyasa), `Birleşik` (sabit 90% piyasa, 10% model logit harmanı) ve [uydurulmuş katsayılar](docs/kanit/harman.json) mevcutsa `Harman` değerlerini görmek için bir `tahmin` eşleşmesine `@1.65/2.30` ekleyin. `topla --sbr-izni` üzerinden SBR oran toplama yazılı izin gerektirir.
- **Diğer ligler:** Asya, bölgesel, yerel ve CBA geriye dönük değerlendirmeleri (ve kısmi sezon uyarıları) [docs/INDEX.md](docs/INDEX.md) altında belgelenmiştir. [docs/sonuclar.md](docs/sonuclar.md) içindeki tarihsel anlık görüntüler eski yokluk özelliklerini içerir ve güncel maç önü performansı olarak sunulmamalıdır.

## Kurulum

**Python 3.12+** gerektirir (Node.js 18+ yalnızca eski `scripts/fetch.mjs` toplayıcısı için gerekir).

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
```

İsteğe bağlı salt okunur yerel MCP sunucusu eklentisi: `python -m pip install -e '.[mcp]'`.

Depoda bulunan Parquet dosyaları hemen kullanılabilir. `requirements-lock.txt` daha eski bir Windows ortamını kaydeder ve makineye özgü bir editable-install yolu içerir; `requirements.txt` taşınabilir doğrudan bağımlılık tanımıdır.

## Sık kullanılan komutlar

```bash
# 1. Yerel tarayıcı uygulamasını aç (basketbol ve futbol panoları)
python -m bbtahmin app

# 2. Günlük basketbol yenilemesini çalıştır, maç önü tahminlerini dondur ve rapor/daily/latest.md dosyasını yaz
python -m bbtahmin gunluk --guncelle

# 3. Varsayımsal ondalık oranlarla bir maç önü basketbol tahminini incele
python -m bbtahmin tahmin "BOS - LAL @1.65/2.30" --lig NBA --tarih 2026-10-25T20:00 --json

# 4. Deneysel İddaa basketbol bülten anlık görüntüsünü yenile (3 salt okunur GET)
python -m bbtahmin bulten --guncelle --limit 10

# 5. Etkin futbol sezonlarını yenile ve 7 günlük maç önü tahminlerini dondur
python -m bbtahmin futbol daily --refresh --days 7

# 6. Çevrimdışı test paketini çalıştır (veya `python -m bbtahmin backtest --ilk-test 2021 --cikti docs/kanit/pregame_verified` ile çekirdek backtest'i yeniden üret)
python -m pytest -q
```

## Veri, lisans ve belgeler

- **Veri:** depoda bulunan Parquet arşivleri `data/` altındadır ve kurulumdan hemen sonra kullanılabilir. Ham indirme önbellekleri (`data/raw/`), yerel bülten geçmişi (`data/bulten/`) ve yerel günlük raporlar (`rapor/`) gitignore kapsamındadır. Tablo şemaları ve kaynak kökeni için bkz. [data/KAYNAKLAR.md](data/KAYNAKLAR.md) ve [docs/data-expansion.md](docs/data-expansion.md).
- **Lisans:** depo kodu [MIT Lisansı](LICENSE) ile lisanslanmıştır. Üçüncü taraf tarihsel veri arşivleri kendi kaynak lisanslarını ve atıflarını korur (CC0, CC BY-SA 4.0 ve ODC-By 1.0 dahil); bkz. [data/KAYNAKLAR.md](data/KAYNAKLAR.md), [data/football/ARGENTINA-LICENSE-DATOS.md](data/football/ARGENTINA-LICENSE-DATOS.md) ve veri kümesi bazındaki belgeler.
- **Belgeler:** konuya göre gruplanmış tam dizin için [docs/INDEX.md](docs/INDEX.md) sayfasına bakın. Ayrıntılı sürüm geçmişi ve önceki README bölümleri olduğu gibi [docs/CHANGELOG.md](docs/CHANGELOG.md) dosyasına taşınmıştır.

[Güvenlik politikası](SECURITY.md) · [Depo güvenlik denetimi](SECURITY_AUDIT.md)
