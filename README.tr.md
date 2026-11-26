[English](README.md)

# Basketbol ve Futbol Maç Tahminleri

`bbtahmin`, maç öncesi basketbol ve futbol tahminleri için bir Python araştırma projesi. Yerel uygulamayı açın, GitHub Actions’ın yayımladığı tahminlere bakın veya depodaki arşivlerle tarih sırasına göre yapılan değerlendirmeleri yeniden çalıştırın.

[![Testler](https://github.com/Bluetwinklez/basketbol-tahmin/actions/workflows/tests.yml/badge.svg)](https://github.com/Bluetwinklez/basketbol-tahmin/actions/workflows/tests.yml)
[![Spor verisi yenileme](https://github.com/Bluetwinklez/basketbol-tahmin/actions/workflows/sports-data.yml/badge.svg)](https://github.com/Bluetwinklez/basketbol-tahmin/actions/workflows/sports-data.yml)

[Güncel performans karnesi](docs/kanit/live_scorecard/scorecard.md) · [Eşleştirilmiş deney durumu](data/improvement_shadow/latest.json) · [Belgeler](docs/INDEX.md) · [Değişiklik geçmişi](docs/CHANGELOG.md)

## Hızlı başlangıç

Depoyu klonlayın ve komutları depo kökünden çalıştırın. Python 3.12 veya üstü gerekir.

```bash
git clone https://github.com/Bluetwinklez/basketbol-tahmin.git
cd basketbol-tahmin
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m bbtahmin app
```

Uygulama `http://127.0.0.1:8765` adresinde açılır. Futbol panosu `/football`, ölçülen isabet ve olasılık kayıpları `/performance` altında yer alır. Uygulama için Node.js derlemesi gerekmez. Arayüz testlerinde Node.js 22 kullanılır. [Yerel uygulama rehberi](docs/local-app.md)

## Neler tahmin ediliyor?

| Spor | Çıktılar | Kapsam |
| --- | --- | --- |
| Basketbol | Kazanan olasılığı, takım skorları, fark, toplam sayı ve belirsizlik aralıkları | NBA, EuroLeague, EuroCup ve Avustralya NBL çekirdek tarihsel modelleri. KBL, ABA, Türkiye BSL, EuroCup Women, FIBA Europe Cup ve diğer organizasyonlar için ayrı arşivler ve modeller. |
| Futbol | Normal süre 1/X/2, beklenen goller, gol toplamları ve karşılıklı gol. Pano ayrıca 1/X/2’den çifte şans hesaplar. | Avrupa ve Amerika liglerinin arşivleri. Zamanlanmış tahmin için güncel ve bağımsız biçimde doğrulanmış başlangıç saati ile yeterli takım geçmişi gerekir. Varsayılan model rakibe göre düzeltme yapar. |

Tarihsel kapsam, elle girilen tahminler ve zamanlanmış tahminler farklı kaynaklara dayanır. NBA geçmişi ve elle girilen NBA tahminleri kullanılabilir. Otomatik NBA fikstürü şu anda kaynak erişimine takılıyor. Japonya 2026–27 B.PREMIER/B.ONE için tahminler etkinleştirilmeden önce ayrı model doğrulaması gerekiyor. [Lig kapsamı](docs/delivery-scope.md) · [NBA durumu](docs/nba-daily.md) · [Kaynak istisnaları](docs/refresh-known-missing.md)

## Komutlar ve çıktılar

| İşlem | Komut | Çıktı |
| --- | --- | --- |
| Kayıtlı basketbol kaynaklarıyla çalıştır | `python -m bbtahmin gunluk --ligler E KBL` | `rapor/daily/` altında yerel tahminler ve günlük rapor |
| Basketbol kaynaklarını yenile ve çalıştır | `python -m bbtahmin gunluk --ligler E KBL --guncelle` | Yerel çalıştırmadan önce açık kaynakları yeniler |
| Kayıtlı futbol kaynaklarıyla çalıştır | `python -m bbtahmin futbol daily --days 7` | `rapor/football/latest.json` altında yerel rapor |
| Futbol kaynaklarını yenile ve çalıştır | `python -m bbtahmin futbol daily --refresh --days 7` | Güncel arşivi ve fikstür doğrulamalarını yeniler |
| Elle NBA tahmini üret | `python -m bbtahmin tahmin "BOS - LAL @1.65/2.30" --lig NBA --json` | Deneysel oran karşılaştırması içeren JSON |
| Deneysel İddaa bültenini oku | `python -m bbtahmin bulten --guncelle --limit 10` | Yerel bülten kopyasını yeniler ve okur |
| Çevrimdışı karneyi yeniden oluştur | `python scripts/live_scorecard.py` | `docs/kanit/live_scorecard/` altında Markdown ve JSON |
| Sabitlenmiş tahmin dosyalarını denetle | `python scripts/pin_improvement_baseline.py --verify-only` | Orijinal dosyaların özet değerlerini doğrular |

[GitHub veri akışı](.github/workflows/sports-data.yml), sonuçları depoya kaydedilen tahmin defterlerinde ve karnelerde yayımlar. Yerel günlük komutlar varsayılan olarak `rapor/` dizinini kullanır. İlk yerel tahminleri korumak için aynı çıktı dizinini yeniden kullanın. Mevcut bir deneyin durumunu yayımlanmış rapordan veya `python scripts/run_shadow_cycle.py --settle-only` komutuyla kontrol edin. [Günlük akış](docs/daily-workflow.md) · [Futbol akışı](docs/football.md)

## Performans ve kanıt

Performans karnesi, sonucu kaydedilen maç öncesi tahminleri ölçer. Örneklem sayısını, isabeti, log loss ve Brier skorlarını, kalibrasyonu ve kıyas modellerini gösterir. Tarihler, dışarıda bırakılan maçlar ve sonuçlar sürümlenen rapordadır. Güven filtresini değerlendirirken isabetle birlikte kaç maç seçildiğine de bakın. Tarihsel denemeler ve ileriye dönük eşleştirilmiş deneyler ayrı kanıtlara dayanır.

| Kanıt | Kaynak |
| --- | --- |
| Kaydedilen tahminler ve gözlenen sonuçlar | [Performans karnesi](docs/kanit/live_scorecard/scorecard.md) · [Yöntem](docs/live-scorecard.md) |
| Aynı maç için dondurulan referans ve aday model | [Yayımlanan deney raporu](data/improvement_shadow/latest.json) · [İyileştirme planı ve kabul koşulları](docs/improvement-progress.md) |
| Tekrarlanabilir tarihsel karşılaştırmalar | [Basketbol geçmiş testleri](docs/kanit/pregame_verified/completed_seasons.csv) · [Futbol ve basketbol değerlendirmesi](docs/accuracy-review.md) · [Fikstür yoğunluğu deneyi](docs/kanit/improvement/basketball-rest-decay.md) |
| Eşleşen tarihsel NBA örnekleminde kapanış oranları | [Piyasa karşılaştırması](docs/kanit/piyasa.csv) · [Simülasyon](docs/kanit/bahis.csv) |

Tahminler araştırma amaçlıdır. Proje bahis işlemi yapmaz veya getiri garantisi vermez. Eksik kaynaklar, doğrulanmamış başlangıç saatleri ve inceleme bekleyen sonuçlar raporlarda görünür.

## Geliştirme ve veri

```bash
python -m pytest -q
npm ci --no-audit --no-fund
npm run test:ui
```

İsteğe bağlı salt okunur yerel MCP sunucusunu `python -m pip install -e '.[mcp]'` ile kurup `bbtahmin-mcp` ile açabilirsiniz. Taşınabilir kurulum için `requirements.txt` kullanın. `requirements-lock.txt` eski bir Windows ortamının kaydıdır.

Kod [MIT lisanslıdır](LICENSE). Arşivlerin [kaynak lisansları ve atıfları](data/KAYNAKLAR.md) ayrıdır. Ham önbellekler, yerel bülten geçmişi ve yerel raporlar Git’e dahil edilmez. [Güvenlik politikası](SECURITY.md) · [Güvenlik denetimi](SECURITY_AUDIT.md)
