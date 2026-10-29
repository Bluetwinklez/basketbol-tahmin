# Basketbol tahmin: geliştirme planı (Codex'e devir)

Hazırlanma: 29 Ekim 2026. Hazırlayan: Claude Code (bu makinedeki oturum).
Repo: `Bluetwinklez/basketbol-tahmin` (herkese açık). Yerel klasör: `C:\Users\Administrator\Desktop\claude\basketbol-tahmin`.

Bu belge iki bölümden oluşur:

1. Bu oturumda yapılanlar ve öğrenilenler (bağlam).
2. Sırayla yapılacak işler: her biri için dosyalar, adımlar, kabul ölçütü ve tuzaklar.

---

## 0. Önce bunları oku: çalışma kuralları

### Ortam (Windows VDS)

- Python ortamı `C:\Tools\bbtahmin-venv\Scripts\python.exe`. Komutlara `PYTHONUTF8=1` ver.
  - `-I` ile çalışırken bu değişken yok sayılır, onun yerine `-X utf8` kullan.
  - Bunu atlarsan Türkçe karakterli çıktılar `cp1252` hatası verir.
- Komut örnekleri:
  - CLI: `PYTHONUTF8=1 C:/Tools/bbtahmin-venv/Scripts/python.exe -m bbtahmin <komut>`
  - Test: `C:/Tools/bbtahmin-venv/Scripts/python.exe -X utf8 -m pytest -q -p no:cacheprovider tests`
- Git kimliği global olarak ayarlı değil. Repodaki commit'ler şu kimliği kullanıyor:
  `git -c user.name=Bluetwinklez -c user.email=144558175+Bluetwinklez@users.noreply.github.com commit ...`
- `gh` CLI giriş yapmış durumda. PR açılabilir.

### Doğruluk kaynağı `origin/main`

- Yerel `main` dalı ESKİ (`a4cbbef`). `origin/main` ise bulut oturumlarının yaklaşık 100 commit'iyle ilerledi ve geçmişi yereldekinden farklı: ortak ata yok.
- Bu yüzden her işe şöyle başla: `git fetch origin && git switch -c <dal> origin/main`.
- Yerel `main` dalından dal açma. Açarsan PR "no history in common" hatası verir.

### Sızıntı yasağı (projenin temel kuralı)

- Bir maçın özelliği yalnızca o maçtan önce bilinebilecek bilgiden üretilir.
- Maçta kimin oynadığı ancak maçtan sonra bilinir. Böyle bir bilgi özelliğe girmez.
  - Örnek: `eksik_ozellik.py` tam olarak bu yüzden kapatıldı (`EKSIK_LIGLERI = set()`, commit `08857a8`). TEKRAR AÇMA.
- Hiperparametre, eşik ve özellik seçimi yalnızca test sezonundan önceki sezonlarla yapılır.
- Test sonucuna bakıp seçim yapmak yasak. Bir değişiklik bazı liglerde iyi, bazılarında kötüyse "iyi olanları seçmek" de yasak, çünkü bu da veriye uydurmadır.
- Her yeni özellik için bir test yaz: hedef maçın ya da sonraki maçların sonucunu değiştir, özelliğin değişmediğini doğrula.
  - Örnekler: `tests/test_leakage.py`, `tests/negative_control.py`.

### Ölçüm kuralları

- Ana metrik log loss. Yanında Brier ve isabet de raporlanır.
- Önce/sonra karşılaştırması her zaman aynı maçlarda, aynı sezonlarda ve aynı veriyle yapılır.
- Varsayılan modele alma eşiği:
  - Tamamlanmış sezonların çoğunda log loss iyileşmeli.
  - Toplam iyileşme en az 0,002 olmalı. Daha azı gürültü sayılır.
- Kanıt dosyaları:
  - Güncel ve geçerli değerlendirme `docs/kanit/pregame_verified/`.
  - `docs/kanit/metrikler.csv` ESKİ: 22 Ekim'de, sızıntılı özellik açıkken üretildi. Ona güvenme (bkz. Faz 1).

### Bilinen durumlar

- Windows'ta `tests/test_shadow.py` içinde 3 test, değişiklik yapılmadan da başarısız oluyor. CI'da (Linux) geçiyorlar.
- Bu 3 testi değişikliklerinin kırdığını sanma. Ama Faz 1'de nedenine bak.
- Tam geriye dönük test uzun sürüyor. NBA verisi 1993-94'ten başladığı için yalnız NBA bile yaklaşık 30-40 dakika.
  - Arka planda çalıştır.
  - Deneme çıktısını `--cikti docs/deneme-<ad>` klasörüne yaz. `docs/deneme*` gitignore'da.

---

## 1. Bu oturumda yapılanlar (29 Ekim 2026)

### 1.1 Durum incelemesi

- Bulut oturumunun raporunu inceledim. O oturum PR #29'u açtı: dal `claude/brave-meitner-ni0oto`, durum draft, birleştirilmedi.
- PR #29 içeriği:
  - Basketbolda 7 ek özellik ve lig bazlı özellik seçimi.
  - Futbolda varsayılan modelin "opponent" modeline geçmesi.
  - Windows'ta kaydedilen tahmin dosyalarının Linux'ta açılamaması hatasının düzeltilmesi.
- PR #29 kendi ölçümüne göre basketbolda gürültü düzeyinde fark yaratıyor:
  - NBA +0,25 puan, NBL +0,6 puan, EuroLeague değişmedi, EuroCup −0,1 puan.
  - Futbol 1/X/2 isabeti %47,8'den %49,2'ye çıkıyor.
- PR #29'un vardığı sonuç: model yalnızca geçmiş skorlardan öğreniyor ve bu verinin tavanına yaklaştı. Gerçek kazanç ancak üç yeni bilgiden gelebilir: bahis oranları, kadro bilgisi ve maç öncesi sakatlık bilgisi.

### 1.2 Kullanıcı kararı: SBR oranları kullanılacak

- Sportsbook Reviews Online (SBR) sitesinin kullanım şartları, içeriğin yazılı izin olmadan kullanılmasını yasaklıyor. Bu yüzden toplayıcı yalnız `--sbr-izni` bayrağıyla çalışıyordu.
- Kullanıcı 29 Ekim'de şartları bilerek kişisel kullanım için onayladı.
- Bunun pratik sonucu: ham oranlar depoya GİRMEZ.
  - `data/oranlar.parquet` artık `.gitignore`'da.
  - Depoya yalnızca özet metrikler girer.

### 1.3 Oran verisi

- SBR'den NBA kapanış moneyline oranları toplandı, `2014-15` ile `2022-23` arası (9 sezon). 2023-24 ve sonrası SBR'de yayımlanmıyor.
- Maç tablosuyla eşleştirme sonucu:
  - 10.692 maç eşleşti, 169 satır eşleşmedi.
  - 166 satırın Basketball Reference'ta karşılığı yok, 3 satırda skor uyuşmuyor.
  - Hem eski hem yeni `maclar.parquet` ile aynı sonuç çıktı.
- Dosya: `data/oranlar.parquet` (yalnızca yerelde). Yeniden üretmek için:
  `python -m bbtahmin topla --ligler NBA --baslangic 2014 --sbr-izni`
  - Bu komut Basketball Reference'ı da yeniden toplar; önbellek `data/raw` altında.
  - Yalnızca oranları üretmek için `veri/nba_odds.collect` ve `match` fonksiyonları ayrıca çağrılabilir.

### 1.4 Kod değişiklikleri (PR #30, dal `feat/nba-oranlar`, commit `f4eb2fa`, `origin/main` tabanlı)

- `src/bbtahmin/backtest.py`
  - `HARMAN_MODELS`, `harman_fit`, `harman_p`, `harman_katsayilari` eklendi.
  - Harman (birleşik tahmin) şöyle çalışıyor: test sezonu S için `y ~ logit(piyasa) + logit(model)` biçiminde cezasız lojistik regresyon kurulur ve yalnızca S'den önceki oranlı sezonlarla eğitilir. Sonuç `piyasa.csv`'ye `harman_<model>` satırları olarak eklenir.
  - Tüm oranlı sezonlarla öğrenilen katsayılar `docs/kanit/harman.json` dosyasına yazılır.
- `src/bbtahmin/tahmin.py`
  - `harman(t)` eklendi.
  - Oranla verilen bir NBA maçında (örnek `"Celtics - Knicks @1.65/2.30"`) çıktıya bir `Harman:` satırı eklenir.
- `tests/test_odds.py`: 2 yeni test.
  - Harman katsayıları yalnızca önceki sezonlardan öğreniliyor mu.
  - Oran ya da katsayı yokken `None` dönüyor mu.
- `docs/kanit/piyasa.csv`, `bahis.csv`, `harman.json` eklendi ve README güncellendi.
- CI'daki 6 kontrolün hepsi yeşil. Durum MERGEABLE/CLEAN, PR hâlâ draft.
- Temizlenecek: ilk denemeden kalan `feat/nba-oran-ozelligi` dalı GitHub'da duruyor. Bu dal eski yerel `main` tabanlı ve kullanılmayacak.

### 1.5 Sonuçlar (NBA, 2017-18 ile 2022-23 arası, aynı 6.758 maç, güncel sızıntısız kod)

| Model | İsabet | Log loss |
|---|---|---|
| Skor modeli | %64,53 | 0,6276 |
| Topluluk | %64,75 | 0,6275 |
| Vig'siz kapanış piyasası | **%66,94** | **0,6070** |
| Harman (skor) | %66,94 | 0,6070 |
| Harman (topluluk) | %67,09 | 0,6070 |

- Modelin harmandaki katsayısı −0,01 ile +0,04 arasında, yani sıfıra yakın. Model, piyasanın bilmediği hiçbir şey bilmiyor.
- Bahis simülasyonu:
  - Eşik yalnızca önceki sezonlardan seçildi.
  - Sabit pay ve çeyrek Kelly denendi; ortalama ROI −%6,4 ile −%2,6 arasında.
  - Kâr eden yöntem yok.
- Piyasa ile model arasındaki fark 0,02 log loss. Bu, tek tek özelliklerin getirdiği kazancın (0,002'nin altı) yaklaşık 10 katı.

### 1.6 Düzeltilen yanlış

- Bu oturumda önce "sakatlık özelliği zaten modelde, log loss'u 0,6220'den 0,6169'a indirdi" demiştim. Bu YANLIŞTI.
- O kazanç, maçta kimin oynadığı bilgisini kullanan sızıntıdan geliyordu. Özellik `08857a8` ile doğru olarak kapatıldı.
- `docs/kanit/metrikler.csv` dosyasındaki NBA satırları hâlâ o sızıntılı koşudan kalma. Güncel kodla NBA skor modelinin log loss'u her sezon 0,002 ile 0,009 arası daha yüksek çıkıyor.

---

## 2. Yapılacaklar (öncelik sırasıyla)

Her faz kendi dalında ve kendi PR'ında yapılsın. Dal her zaman `origin/main`'den açılsın. PR'lar draft açılsın.

### Faz 1: temizlik ve güvenilir başlangıç ölçümü (küçük, önce bu)

1. **PR #30'u birleştir** (kullanıcı onayıyla).
   - Sonra eski `feat/nba-oran-ozelligi` dalını sil: `git push origin --delete feat/nba-oran-ozelligi`.
2. **PR #29 ile çakışmayı kontrol et.**
   - İki PR da `backtest.py`'ye dokunuyor. Hangisi önce birleşirse, diğeri `origin/main` ile güncellensin ve testler yeniden çalıştırılsın.
3. **Eski kanıtları yenile.**
   - `docs/kanit/metrikler.csv`, `toplam.csv`, `tahminler.csv` ve `docs/sonuclar.md` sızıntısız kodla yeniden üretilsin. Ya da README bu dosyaların yerine `docs/kanit/pregame_verified/` dosyasını kaynak göstersin.
   - Hangi dosyanın geçerli olduğu tek bir yerde açıkça yazılsın.
   - Piyasa kıyası (`piyasa.csv`, `bahis.csv`, `harman.json`) de `pregame_verified` akışına taşınsın, böylece manifest ve hash kontrolüne girsin.
   - Kabul ölçütü: README'deki her NBA sayısı, tek bir manifest'li kanıt klasöründen yeniden üretilebilmeli.
4. **Windows'ta başarısız olan 3 testi incele** (`tests/test_shadow.py`).
   - Olası nedenler: yol ayırıcı, satır sonu ya da saat dilimi.
   - Ürün kodunda gerçek bir hata varsa düzelt. Yalnız test ortamı sorunuysa testi platformdan bağımsız hale getir.
   - Kabul ölçütü: Windows'ta tam test paketi yeşil.

### Faz 2: maç öncesi NBA sakatlık geçmişi (en yüksek beklenen getiri)

**Amaç:** Kapatılan eksik oyuncu özelliğinin sızıntısız sürümü. Eksik oyuncu kümesi maçtan sonraki kadrodan değil, **maçtan önce yayımlanmış son resmi sakatlık raporundan** alınır.

**Gerekçe:** Piyasa ile model arasındaki 0,02'lik log loss farkının önemli bir kısmı kadro bilgisinden geliyor. Sızıntılı sürüm 0,005 civarı kazanç göstermişti. Sızıntısız sürümün kazancı bunun altında olacaktır, ama gerçek olur.

**Mevcut parçalar:**

- `src/bbtahmin/veri/sakatlik.py`
  - URL kalıbı: `https://ak-static.cms.nba.com/referee/injury/Injury-Report_{YYYY-MM-DD}_{HH_MM}{AM,PM}.pdf` (ABD Doğu saati).
  - PDF `pdfplumber` ile ayrıştırılıyor. `son_rapor(an, geriye_saat=30)` fonksiyonu verilen andan önceki son raporu buluyor.
- `src/bbtahmin/player_context.py`
  - `archive_injuries` ve `sakatlik-arsivle` komutu yalnızca ŞİMDİKİ raporu arşivliyor.
  - `data/observations/injuries/` altında 22 Ekim'den bu yana yalnızca 12 rapor var.
- `src/bbtahmin/eksik_ozellik.py`: oyuncu değeri ve dakika üstel ortalaması hazır, önceki maçlardan hesaplanıyor. Değiştirilecek tek şey eksik oyuncu kümesinin kaynağı.
- `data/nba_oyuncu_mac.parquet`, `data/nba_oyuncu_istatistik.parquet`: oyuncu-maç satırları.

**Adımlar:**

1. **Geçmiş raporları geriye doğru topla.**
   - Yeni komut `sakatlik-gecmis-topla --baslangic 2021-10-01 --bitis <dün>`.
   - Her maç günü için o günün raporlarını sırayla dene. Gün içinde saatlik ya da yarım saatlik yayımlanıyorlar; dosya adındaki saat yayım zamanıdır.
   - Önbellek: `data/raw/nba_injury/`, git dışında.
   - Ayrıştırılmış çıktı: `data/nba_sakatlik_gecmis.parquet`. Sütunlar: `rapor_zamani_utc, mac_tarihi, takim, oyuncu, durum, neden`.
   - Hız sınırı: en az 3 saniye aralık, tanımlı bir User-Agent ve robots.txt kontrolü. 404 normaldir (o saatte rapor yok); ağı gereksiz yorma.
   - Kapsam notu: bu URL biçiminin hangi tarihten itibaren var olduğunu ÖNCE doğrula. 2021-22'den önce biçim farklı olabilir. Bulduğunu `data/KAYNAKLAR.md` dosyasına yaz.
2. **Her maça bir rapor bağla.**
   - Her maç için kullanılacak rapor, `tipoff_utc - 30 dk` anından önce yayımlanmış son rapordur.
   - Maç saati `maclar.tarih_utc` sütunundan alınır. Saat bilinmiyorsa (yalnız tarih varsa) o günün yerel saatiyle 12:00 ET öncesindeki son rapor alınır; bu korumacı bir yaklaşımdır.
   - Rapor bulunamayan maçta özellik `NaN` olur ve modelde eksik değer bayrağı tutulur.
3. **İsim eşleştir.**
   - Rapordaki "Soyad, Ad" biçimini `oyuncular_nba.parquet` kimlikleriyle eşleştir.
   - Eşleşmeyenleri say ve raporla. Hedef: Out/Doubtful oyuncuların en az %98'i eşleşsin.
4. **Özelliği yeniden tanımla.**
   - `eksik_ozellikleri(..., kaynak='rapor')` parametresi ekle. Eksik oyuncu kümesi = rapordaki `Out` (ayrı bir deneyde `Out + Doubtful`).
   - `Questionable` için ayrı bir özellik dene: `belirsiz_dk_diff`.
   - Oyuncu değeri ve dakika hesabı değişmez; yalnızca önceki maçlardan hesaplanmaya devam eder.
5. **Sızıntı testi ekle.**
   - Hedef maçın oyuncu satırlarını ya da sonraki raporları değiştir, özellik değişmemeli.
   - Rapor zamanı tipoff'tan sonraysa kullanılmadığını doğrula.
6. **Ölç.**
   - Önce: `pregame_verified` NBA. Sonra: aynı maçlar (2021-22'den itibaren, rapor kapsamı içinde), aynı kod, yalnızca yeni özellik eklenmiş.
   - Rapor kapsamı dışındaki sezonlarda özellik eksik olacağı için iki seçenek var:
     - Ya modeli 2021-22'den itibaren ayrı eğit,
     - Ya da eksik değer bayrağıyla tüm geçmişi kullan.
   - Hangisinin seçildiğini önceden belgeye yaz; sonuçlara bakıp değiştirme.
   - Piyasaya karşı da ölç. Oranlı sezonlar 2022-23 ile sınırlı olduğu için örtüşme tek sezon kalır; bunu açıkça yaz.
7. **Kabul ölçütü:**
   - Rapor kapsamındaki tamamlanmış sezonların çoğunda log loss iyileşmeli ve toplam iyileşme en az 0,002 olmalı. Bu sağlanırsa `EKSIK_LIGLERI = {'NBA'}` yeni kaynakla açılır.
   - Sağlanmazsa kod araştırma olarak kalır ve sonuç README'ye "denendi, alınmadı" diye yazılır.
8. **Canlı tahmin:** `tahmin --sakatlik` artık modele girer. Şu an yalnızca gösterim amaçlı. Geçmiş testle aynı kural uygulanır: tipoff'tan 30 dakika önceki son rapor.

### Faz 3: oyuncu bazlı takım gücü

**Amaç:** Takım gücünü yalnızca takım sonuçlarından değil, **oynaması beklenen oyuncuların** puanlarından hesaplamak. Böylece sezon başı transferleri ve uzun süreli sakatlıklar kendiliğinden yakalanır. Bu, Avrupa'da en çok zorlanılan nokta.

**Veri:**

- NBA: `nba_oyuncu_istatistik.parquet`, yaklaşık 1,07 milyon oyuncu-maç satırı.
- Avrupa: `avrupa_oyuncu_istatistik.parquet` ve `avrupa_olaylar.parquet` (maç akışı, 625 bin olay).

**Adımlar:**

1. **Oyuncu puanı.**
   - Her oyuncu için yalnızca önceki maçlardan bir puan hesapla: 100 hücum başına net katkı.
   - İlk sürüm basit olsun: +/- değerinin dakikaya göre üstel ortalaması, lig ortalamasına doğru küçültülmüş (az dakikalı oyuncu ortalamaya yakın kalsın).
   - Sonraki sürüm: maç akışından sahadaki beşliler çıkarılıp ridge regresyonla RAPM benzeri puan (bkz. `dblackrun/pbpstats` fikri).
   - Sezon geçişinde puan korunur, takım değişse de oyuncunun puanı onunla gider. Bu, transferleri yakalar.
2. **Beklenen dakika.**
   - Her oyuncu için yalnızca önceki maçlardan bir dakika beklentisi çıkar: son maçlardaki dakikanın üstel ortalaması.
   - Faz 2'deki sakatlık raporunda Out olan oyuncunun beklenen dakikası 0 olur ve dakikası takım arkadaşlarına paylaştırılır.
3. **Takım gücü.**
   - Takım gücü = Σ(beklenen dakika × puan) / 240.
   - Yeni özellikler: `oyuncu_gucu_diff` (ev − deplasman) ve `kadro_devamliligi` (geçen sezonun dakikalarının bu kadroda kalan payı).
4. **Sızıntı testi.**
   - Hedef maçın kutu skorunu değiştir, özellik değişmemeli.
   - Bir günün sonuçları ancak ertesi UTC gününden itibaren özelliğe girer (mevcut kural).
5. **Ölçüm** NBA, EuroLeague ve EuroCup'ta ayrı ayrı yapılır.
   - Avrupa'da oyuncu verisi maç geçmişinden daha geç başlıyor. Kapsam farkını rapora yaz.
   - Kapsam dışı maçlarda eksik değer bayrağı kullanılır.
6. **Kabul ölçütü:** Faz 2 ile aynı.
   - Ayrıca sezonun ilk 10 maçındaki iyileşmeyi ayrıca raporla; beklenen kazanç orada.
   - Bir lig iyileşip öteki kötüleşirse lig bazlı seçim yalnızca önceki sezon sonucuna göre yapılır (PR #29'daki kural).

### Faz 4: kendi oran arşivimiz (iddaa)

**Durum:**

- `.github/workflows/observations.yml` her gün 20:15 ve 23:15 UTC'de iddaa bültenini ve NBA raporlarını arşivliyor.
- `data/observations/odds/` altında 23 Ekim'den bu yana yaklaşık 11 kayıt var.
- `src/bbtahmin/market_history.py` bu kayıtları gelecek oranları sızdırmadan okuyor.
- `bulten --gecmis EVENT_ID` komutu var.

**Adımlar:**

1. **Kayıt sıklığını artır.**
   - Günde 2 anlık görüntü (snapshot) kapanış oranı için yetersiz.
   - Maç saatlerine yakın ek zamanlar ekle: Avrupa maçları için 16:00 ve 18:30 UTC, NBA için 23:00 UTC.
   - GitHub Actions'ın kotasını ve commit gürültüsünü göz önünde tut. Gerekirse günlük dosyaları tek bir dosyada birleştir.
2. **Maç başına "son maç öncesi oran" tablosu.**
   - Her etkinlik için `start_utc`'den önceki son gözlemi `data/oran_gozlem.parquet` dosyasına yaz.
   - Bunu "kapanış oranı" diye ETİKETLEME. Doğru ad: "son gözlenen maç öncesi oran".
   - İddaa etkinlik kimliğini `maclar.mac_id` ile eşleştir: takım adı eşleme, lig ve ±6 saat. Eşleşmeyenleri say.
3. **Kayıtların aksamadığını denetle.**
   - Atlanan gün, şema değişikliği ve boş bülten için bir kontrol ekle; `monitoring.py` ya da `archive_checks.py` kullanılabilir.
   - Kayıt durursa CI'da uyarı versin.
4. **Ölçüm (yaklaşık 3 ay sonra):**
   - Lig bazında model ile iddaa'nın vig'siz olasılığını aynı maçlarda karşılaştır. Harman için `backtest.harman_*` fonksiyonlarını yeniden kullan.
   - iddaa marjı yüksek olduğu için vig'i oransal olarak çıkar; Shin yöntemi ayrı bir deney olabilir.
   - Alt/üst toplamlarında model toplamı ile iddaa çizgisini karşılaştır. `market_estimates.py` şu an yalnızca gösterim amaçlı.

### Faz 5: piyasanın zayıf olduğu yerleri bulmak (Faz 4 verisi biriktikten sonra)

- **Hipotez:** NBA'de kazananı tahmin ederek piyasayı geçmek gerçekçi değil (ölçüldü). Daha umut verici alanlar:
  - Küçük Avrupa ve yerel ligler: BSL, ABA, KBL, NBL vb.
  - Alt/üst toplamları.
  - Sezonun ilk haftaları.
- **Başarı ölçütü:** Önceden belirlenmiş liglerde, arşivlenen iddaa oranlarına karşı:
  - Log loss farkı ve önyükleme (bootstrap) güven aralığı.
  - Yalnızca önceki dönemden seçilmiş eşikle sözde bahis getirisi.
  - Eşik ve lig listesi sonuçlar görülmeden yazılır.
- **İleriye dönük (prospektif) doğrulama:**
  - `prospective.py` ve `shadow.py` zaten var: tahmin dondurulur, sonuç sonradan puanlanır.
  - Her yeni varsayılan model, en az bir ay bu "gölge" kayıtta çalışıp eski modelle eşleştirilmiş karşılaştırmayı geçmeden canlıya alınmaz.

---

## 3. Yapılmaması gerekenler

- Aynı geçmiş skorlardan yeni küçük özellikler türetmek. Ölçüldü: etkisi 0,002'nin altında. PR #29 ve `docs/kanit/feature_research/` bunu gösteriyor.
- Sezon başı aşırı güven kalibrasyonu, takım gücünü EuroCup'tan EuroLeague'e aktarmak, ligden uzun süre ayrı kalıp dönen takımın reytingini sıfırlamak. Hepsi denendi ve sonuç karışık ya da olumsuz çıktı (PR #29).
- Maçta kimin oynadığı bilgisini özellik olarak kullanmak.
- SBR ham oranlarını ya da başka şartlı verileri herkese açık repoya koymak.
- Ücretli API'ye abone olmak ya da kullanıcıdan anahtar istemek. Kullanıcı kararı gerekir.
- `docs/kanit/` altındaki eski sonuçları yeni sonuç gibi yeniden etiketlemek.

## 4. Teslim biçimi (her faz için)

- `origin/main`'den bir dal, draft bir PR. PR açıklamasında:
  - Önce/sonra tablosu: aynı maçlar ve sezonlar; isabet, log loss ve maç sayısı.
  - Ne denendiği ve ne alınmadığı.
  - Sızıntı testlerinin listesi.
- Windows'ta ve CI'da testler yeşil.
- README ve ilgili `docs/` sayfası güncel. Yeni veri kaynakları `data/KAYNAKLAR.md` dosyasına yazılır.
