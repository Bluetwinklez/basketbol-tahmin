# Veri

Bu klasördeki parquet dosyaları, kaynaklardan derlenmiş işlenmiş maç ve oyuncu verileridir. Yalnızca skorlar, kutu skor toplamları ve oyuncu süreleri gibi kamuya açık spor istatistiklerini içerir.

| Dosya | İçerik |
|---|---|
| `maclar.parquet` | Maç sonuçları: EuroLeague, EuroCup, NBA, NBL. `kaynak` sütunu her satırın geldiği adresi gösterir. |
| `kutu.parquet`, `kutu_nba.parquet` | Takım kutu skor toplamları |
| `oyuncular.parquet`, `oyuncular_nba.parquet` | Maç başına oyuncu süreleri |
| `nba_oyuncu_mac.parquet` | NBA oyuncu maç kayıtları: dakika, artı/eksi (nba_api) |
| `nba_takim_istatistik.parquet`, `nba_oyuncu_istatistik.parquet` | ESPN/sportsdataverse arşivlerinden ayrıntılı NBA takım ve oyuncu kutu skorları |
| `nba_mac_baglami.parquet` | NBA kaynak maç kimliği, saha, tarafsız saha ve periyot sayısı |
| `avrupa_takim_istatistik.parquet`, `avrupa_oyuncu_istatistik.parquet` | Resmi maçlarla eşleştirilen Avrupa kutu skoru ayrıntıları |
| `avrupa_sutlar.parquet`, `avrupa_olaylar.parquet` | Maç sonrasında gözlenen şut koordinatları ve yapılandırılmış olay kodları; aynı maçın maç öncesi özelliği olarak kullanılamaz |

Kaynaklar: EuroLeague canlı API, Basketball-Reference, stats.nba.com (nba_api), ESPN, nblR verisi.

Genişletilmiş arşiv: [sportsdataverse-data](https://github.com/sportsdataverse/sportsdataverse-data)
ve [euroleague-open-data](https://github.com/McNews11/euroleague-open-data).
Kaynak adresleri tablolarda, snapshot özeti `docs/kanit/avrupa_detay.json` içinde;
kapsam ve kullanım ayrıntıları [docs/data-expansion.md](../docs/data-expansion.md) dosyasındadır.

Ham indirme önbelleği (`data/raw/`) yayınlanmaz. Bu klasördeki üçüncü taraf sayfaları, PDF'ler ve API cevapları olduğu gibi yeniden dağıtılmamalıdır. Gerekirse `python -m bbtahmin` toplama komutlarıyla yeniden oluşturulur.
