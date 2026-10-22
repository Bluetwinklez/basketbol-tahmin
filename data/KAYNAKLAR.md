# Veri

Bu klasördeki parquet dosyaları, kaynaklardan derlenmiş işlenmiş maç ve oyuncu verileridir. Yalnızca skorlar, kutu skor toplamları ve oyuncu süreleri gibi kamuya açık spor istatistiklerini içerir.

| Dosya | İçerik |
|---|---|
| `maclar.parquet` | Maç sonuçları: EuroLeague, EuroCup, NBA, NBL. `kaynak` sütunu her satırın geldiği adresi gösterir. |
| `kutu.parquet`, `kutu_nba.parquet` | Takım kutu skor toplamları |
| `oyuncular.parquet`, `oyuncular_nba.parquet` | Maç başına oyuncu süreleri |
| `nba_oyuncu_mac.parquet` | NBA oyuncu maç kayıtları: dakika, artı/eksi (nba_api) |

Kaynaklar: EuroLeague canlı API, Basketball-Reference, stats.nba.com (nba_api), ESPN, nblR verisi.

Ham indirme önbelleği (`data/raw/`) yayınlanmaz. Bu klasördeki üçüncü taraf sayfaları, PDF'ler ve API cevapları olduğu gibi yeniden dağıtılmamalıdır. Gerekirse `python -m bbtahmin` toplama komutlarıyla yeniden oluşturulur.
