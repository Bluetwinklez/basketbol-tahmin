# Gerçek çalıştırma sonuçları

Rapor zamanı (UTC): 2026-10-21T11:11:24.337538+00:00. Toplama: 2026-10-21T10:26:35.152772+00:00.

Tam komutlar ve ortam: [README](../README.md) ve [ortam.txt](kanit/ortam.txt).

Çalıştırma: .venv/Scripts/python.exe -m bbtahmin topla; .venv/Scripts/python.exe -m bbtahmin backtest.

## Toplam değerlendirme

Ev sahibi tabanı p=1 üretir; log loss hesapta 1e-6 ile kırpılır. Fark MAE için ev sahibi tabanı eğitim ortalama farkını, Elo tabanları eğitimde Elo farkından öğrenilen doğrusal regresyonu kullanır. Sınıflandırıcıların MAE değeri ortak Ridge regresyonunundur.

| lig | model | n | log_loss | brier | accuracy | margin_mae |
| --- | --- | --- | --- | --- | --- | --- |
| E | elo | 4621 | 0.6034 | 0.2080 | 0.6745 | 9.4098 |
| E | hist_gradient_boosting | 4621 | 0.6089 | 0.2104 | 0.6704 | 9.2596 |
| E | home | 4621 | 5.1782 | 0.3748 | 0.6252 | 10.1573 |
| E | logistic | 4621 | 0.5983 | 0.2060 | 0.6737 | 9.2596 |
| E | mov_elo | 4621 | 0.5988 | 0.2063 | 0.6786 | 9.3390 |
| NBA | elo | 765 | 0.6293 | 0.2203 | 0.6353 | 9.7305 |
| NBA | hist_gradient_boosting | 765 | 0.6226 | 0.2167 | 0.6497 | 9.7901 |
| NBA | home | 765 | 5.7249 | 0.4144 | 0.5856 | 10.8653 |
| NBA | logistic | 765 | 0.6207 | 0.2161 | 0.6458 | 9.7901 |
| NBA | mov_elo | 765 | 0.6217 | 0.2167 | 0.6497 | 9.8376 |
| U | elo | 3438 | 0.6211 | 0.2157 | 0.6582 | 9.9994 |
| U | hist_gradient_boosting | 3438 | 0.6312 | 0.2200 | 0.6553 | 9.8622 |
| U | home | 3438 | 5.4249 | 0.3927 | 0.6073 | 10.7497 |
| U | logistic | 3438 | 0.6671 | 0.2218 | 0.6527 | 9.8622 |
| U | mov_elo | 3438 | 0.6167 | 0.2138 | 0.6640 | 9.9156 |

## Lig ve sezon bazında yan yana

Hücre: log loss / Brier / doğruluk / fark MAE. İlk iki mevcut sezon yalnız eğitim ve kronolojik doğrulama; test yapılmadı. BasketbolBet: **yapılamadı (referans bulunamadı)**. NBA 2016-17 kısmi sezon: tüm sezona genellenemez.

### E

| sezon | elo | hist_gradient_boosting | home | logistic | mov_elo |
| --- | --- | --- | --- | --- | --- |
| 2009-10 | 0.5531 / 0.1865 / 0.7181 / 10.12 | 0.5705 / 0.1941 / 0.6968 / 9.46 | 5.2176 / 0.3777 / 0.6223 / 10.78 | 0.5420 / 0.1852 / 0.7128 / 9.46 | 0.5402 / 0.1813 / 0.7340 / 10.04 |
| 2010-11 | 0.6208 / 0.2142 / 0.6561 / 10.09 | 0.6206 / 0.2141 / 0.6878 / 9.65 | 4.8976 / 0.3545 / 0.6455 / 10.62 | 0.6095 / 0.2089 / 0.6720 / 9.65 | 0.6156 / 0.2111 / 0.6772 / 10.06 |
| 2011-12 | 0.5598 / 0.1877 / 0.7340 / 9.00 | 0.5828 / 0.1980 / 0.7287 / 9.12 | 5.2176 / 0.3777 / 0.6223 / 10.90 | 0.5568 / 0.1878 / 0.7181 / 9.12 | 0.5457 / 0.1827 / 0.7340 / 8.97 |
| 2012-13 | 0.5640 / 0.1912 / 0.7154 / 9.64 | 0.5720 / 0.1938 / 0.6957 / 9.37 | 5.5699 / 0.4032 / 0.5968 / 10.81 | 0.5618 / 0.1901 / 0.6719 / 9.37 | 0.5595 / 0.1895 / 0.7075 / 9.44 |
| 2013-14 | 0.5620 / 0.1891 / 0.7273 / 9.41 | 0.5668 / 0.1924 / 0.6996 / 9.29 | 5.0784 / 0.3676 / 0.6324 / 10.95 | 0.5483 / 0.1840 / 0.7273 / 9.29 | 0.5547 / 0.1861 / 0.7352 / 9.38 |
| 2014-15 | 0.5378 / 0.1800 / 0.7410 / 8.40 | 0.5435 / 0.1822 / 0.7490 / 8.27 | 5.1739 / 0.3745 / 0.6255 / 9.99 | 0.5348 / 0.1782 / 0.7291 / 8.27 | 0.5341 / 0.1778 / 0.7570 / 8.18 |
| 2015-16 | 0.6114 / 0.2105 / 0.6800 / 10.39 | 0.6083 / 0.2090 / 0.6560 / 10.05 | 4.9183 / 0.3560 / 0.6440 / 10.99 | 0.5959 / 0.2039 / 0.6720 / 10.05 | 0.5988 / 0.2064 / 0.6840 / 10.20 |
| 2016-17 | 0.6183 / 0.2147 / 0.6448 / 8.85 | 0.6153 / 0.2140 / 0.6371 / 8.86 | 5.2275 / 0.3784 / 0.6216 / 9.21 | 0.6144 / 0.2136 / 0.6409 / 8.86 | 0.6144 / 0.2132 / 0.6680 / 8.81 |
| 2017-18 | 0.6131 / 0.2122 / 0.6654 / 9.38 | 0.6224 / 0.2162 / 0.6769 / 9.25 | 5.0480 / 0.3654 / 0.6346 / 9.73 | 0.6103 / 0.2109 / 0.6769 / 9.25 | 0.6157 / 0.2131 / 0.6731 / 9.23 |
| 2018-19 | 0.5742 / 0.1947 / 0.6885 / 9.16 | 0.5702 / 0.1931 / 0.7077 / 8.80 | 5.1542 / 0.3731 / 0.6269 / 10.40 | 0.5610 / 0.1893 / 0.7231 / 8.80 | 0.5693 / 0.1928 / 0.6885 / 9.07 |
| 2019-20 | 0.6002 / 0.2079 / 0.6508 / 9.52 | 0.5885 / 0.2010 / 0.6667 / 9.37 | 5.2631 / 0.3810 / 0.6190 / 10.15 | 0.5831 / 0.2005 / 0.6944 / 9.37 | 0.5846 / 0.2013 / 0.6746 / 9.30 |
| 2020-21 | 0.6552 / 0.2302 / 0.6524 / 9.83 | 0.6764 / 0.2382 / 0.6250 / 9.84 | 5.9811 / 0.4329 / 0.5671 / 10.61 | 0.6693 / 0.2337 / 0.6372 / 9.84 | 0.6544 / 0.2296 / 0.6463 / 9.90 |
| 2021-22 | 0.6212 / 0.2159 / 0.6355 / 9.88 | 0.6311 / 0.2202 / 0.6421 / 9.62 | 4.8516 / 0.3512 / 0.6488 / 9.99 | 0.6178 / 0.2146 / 0.6388 / 9.62 | 0.6162 / 0.2137 / 0.6455 / 9.80 |
| 2022-23 | 0.6327 / 0.2209 / 0.6616 / 9.14 | 0.6389 / 0.2240 / 0.6524 / 9.16 | 5.1808 / 0.3750 / 0.6250 / 9.67 | 0.6338 / 0.2217 / 0.6463 / 9.16 | 0.6323 / 0.2214 / 0.6372 / 9.14 |
| 2023-24 | 0.6057 / 0.2084 / 0.7100 / 9.21 | 0.6034 / 0.2078 / 0.6979 / 9.05 | 4.8834 / 0.3535 / 0.6465 / 9.66 | 0.5913 / 0.2027 / 0.7190 / 9.05 | 0.5998 / 0.2058 / 0.7221 / 9.15 |
| 2024-25 | 0.6274 / 0.2204 / 0.6182 / 9.22 | 0.6312 / 0.2214 / 0.6606 / 9.09 | 5.2750 / 0.3818 / 0.6182 / 9.79 | 0.6216 / 0.2176 / 0.6273 / 9.09 | 0.6212 / 0.2178 / 0.6364 / 9.15 |
| 2025-26 | 0.6301 / 0.2199 / 0.6368 / 9.14 | 0.6400 / 0.2249 / 0.6020 / 9.23 | 5.0176 / 0.3632 / 0.6368 / 9.57 | 0.6354 / 0.2228 / 0.6219 / 9.23 | 0.6383 / 0.2245 / 0.6119 / 9.24 |

### NBA

| sezon | elo | hist_gradient_boosting | home | logistic | mov_elo |
| --- | --- | --- | --- | --- | --- |
| 2016-17 | 0.6293 / 0.2203 / 0.6353 / 9.73 | 0.6226 / 0.2167 / 0.6497 / 9.79 | 5.7249 / 0.4144 / 0.5856 / 10.87 | 0.6207 / 0.2161 / 0.6458 / 9.79 | 0.6217 / 0.2167 / 0.6497 / 9.84 |

### U

| sezon | elo | hist_gradient_boosting | home | logistic | mov_elo |
| --- | --- | --- | --- | --- | --- |
| 2009-10 | 0.6565 / 0.2318 / 0.6410 / 10.88 | 0.6382 / 0.2236 / 0.6282 / 10.43 | 5.2251 / 0.3782 / 0.6218 / 10.30 | 0.6383 / 0.2238 / 0.6603 / 10.43 | 0.6625 / 0.2345 / 0.6667 / 11.39 |
| 2010-11 | 0.6304 / 0.2201 / 0.6000 / 9.07 | 0.6447 / 0.2266 / 0.6129 / 9.23 | 5.4371 / 0.3935 / 0.6065 / 9.83 | 0.6402 / 0.2250 / 0.6194 / 9.23 | 0.6254 / 0.2178 / 0.6194 / 8.91 |
| 2011-12 | 0.5752 / 0.1955 / 0.7179 / 9.12 | 0.6277 / 0.2185 / 0.6410 / 9.11 | 4.8709 / 0.3526 / 0.6474 / 10.57 | 0.5710 / 0.1936 / 0.7179 / 9.11 | 0.5698 / 0.1932 / 0.7115 / 9.01 |
| 2012-13 | 0.6141 / 0.2128 / 0.6815 / 10.25 | 0.6373 / 0.2230 / 0.6752 / 10.65 | 5.9838 / 0.4331 / 0.5669 / 11.43 | 0.6562 / 0.2299 / 0.6178 / 10.65 | 0.6099 / 0.2111 / 0.6624 / 10.32 |
| 2013-14 | 0.6018 / 0.2071 / 0.6858 / 9.61 | 0.6502 / 0.2285 / 0.6339 / 9.59 | 4.8317 / 0.3497 / 0.6503 / 10.68 | 1.0061 / 0.2536 / 0.6393 / 9.59 | 0.6033 / 0.2076 / 0.6831 / 9.53 |
| 2014-15 | 0.6029 / 0.2081 / 0.6787 / 9.72 | 0.6210 / 0.2165 / 0.6656 / 9.78 | 5.5262 / 0.4000 / 0.6000 / 10.44 | 0.6691 / 0.2382 / 0.6000 / 9.78 | 0.6058 / 0.2093 / 0.6787 / 9.80 |
| 2015-16 | 0.6516 / 0.2281 / 0.6447 / 10.12 | 0.6585 / 0.2305 / 0.6612 / 9.88 | 5.5898 / 0.4046 / 0.5954 / 10.59 | 0.6459 / 0.2259 / 0.6480 / 9.88 | 0.6417 / 0.2244 / 0.6678 / 9.90 |
| 2016-17 | 0.6081 / 0.2098 / 0.6644 / 10.77 | 0.6031 / 0.2072 / 0.6986 / 10.59 | 5.2045 / 0.3767 / 0.6233 / 11.01 | 0.6001 / 0.2058 / 0.7055 / 10.59 | 0.6021 / 0.2071 / 0.6849 / 10.72 |
| 2017-18 | 0.6156 / 0.2139 / 0.6630 / 9.58 | 0.6345 / 0.2229 / 0.6522 / 9.45 | 5.5562 / 0.4022 / 0.5978 / 10.55 | 0.6124 / 0.2126 / 0.6630 / 9.45 | 0.6141 / 0.2133 / 0.6413 / 9.47 |
| 2018-19 | 0.5778 / 0.1969 / 0.6720 / 8.64 | 0.5669 / 0.1934 / 0.6935 / 8.39 | 5.2737 / 0.3817 / 0.6183 / 9.82 | 0.5492 / 0.1854 / 0.7043 / 8.39 | 0.5660 / 0.1913 / 0.6989 / 8.51 |
| 2019-20 | 0.6888 / 0.2443 / 0.6071 / 10.22 | 0.6883 / 0.2430 / 0.6250 / 9.68 | 5.0163 / 0.3631 / 0.6369 / 9.74 | 0.6915 / 0.2426 / 0.6250 / 9.68 | 0.6886 / 0.2440 / 0.6012 / 10.11 |
| 2020-21 | 0.6457 / 0.2270 / 0.6162 / 9.87 | 0.6287 / 0.2194 / 0.6486 / 9.64 | 5.7502 / 0.4162 / 0.5838 / 10.47 | 0.6346 / 0.2221 / 0.6270 / 9.64 | 0.6366 / 0.2227 / 0.6270 / 9.72 |
| 2021-22 | 0.6183 / 0.2144 / 0.6614 / 10.47 | 0.6337 / 0.2215 / 0.6561 / 10.24 | 5.2631 / 0.3810 / 0.6190 / 11.18 | 0.6385 / 0.2238 / 0.6561 / 10.24 | 0.6142 / 0.2141 / 0.6508 / 10.26 |
| 2022-23 | 0.5891 / 0.2023 / 0.6667 / 9.26 | 0.6025 / 0.2085 / 0.6513 / 9.51 | 5.2428 / 0.3795 / 0.6205 / 10.34 | 0.6018 / 0.2088 / 0.6410 / 9.51 | 0.5950 / 0.2055 / 0.6615 / 9.52 |
| 2023-24 | 0.6246 / 0.2169 / 0.6667 / 10.58 | 0.6207 / 0.2120 / 0.6769 / 10.10 | 6.4472 / 0.4667 / 0.5333 / 11.71 | 0.5964 / 0.2030 / 0.6974 / 10.10 | 0.6089 / 0.2097 / 0.6615 / 10.29 |
| 2024-25 | 0.6466 / 0.2276 / 0.6327 / 10.39 | 0.6358 / 0.2220 / 0.6480 / 10.10 | 5.4980 / 0.3980 / 0.6020 / 11.19 | 0.6237 / 0.2163 / 0.6735 / 10.10 | 0.6352 / 0.2219 / 0.6684 / 10.16 |
| 2025-26 | 0.6257 / 0.2175 / 0.6564 / 11.88 | 0.6147 / 0.2121 / 0.6769 / 11.60 | 5.7388 / 0.4154 / 0.5846 / 12.91 | 0.6227 / 0.2153 / 0.6564 / 11.60 | 0.6137 / 0.2119 / 0.6718 / 11.50 |

## Toplanan maç sayıları

| lig | sezon | mac_sayisi | durum |
| --- | --- | --- | --- |
| E | 2007-08 | 231 | alındı |
| E | 2008-09 | 188 | alındı |
| E | 2009-10 | 188 | alındı |
| E | 2010-11 | 189 | alındı |
| E | 2011-12 | 188 | alındı |
| E | 2012-13 | 253 | alındı |
| E | 2013-14 | 253 | alındı |
| E | 2014-15 | 251 | alındı |
| E | 2015-16 | 250 | alındı |
| E | 2016-17 | 259 | alındı |
| E | 2017-18 | 260 | alındı |
| E | 2018-19 | 260 | alındı |
| E | 2019-20 | 252 | alındı |
| E | 2020-21 | 328 | alındı |
| E | 2021-22 | 299 | alındı |
| E | 2022-23 | 328 | alındı |
| E | 2023-24 | 331 | alındı |
| E | 2024-25 | 330 | alındı |
| E | 2025-26 | 402 | alındı |
| U | 2007-08 | 323 | alındı |
| U | 2008-09 | 151 | alındı |
| U | 2009-10 | 156 | alındı |
| U | 2010-11 | 155 | alındı |
| U | 2011-12 | 156 | alındı |
| U | 2012-13 | 157 | alındı |
| U | 2013-14 | 366 | alındı |
| U | 2014-15 | 305 | alındı |
| U | 2015-16 | 304 | alındı |
| U | 2016-17 | 146 | alındı |
| U | 2017-18 | 184 | alındı |
| U | 2018-19 | 186 | alındı |
| U | 2019-20 | 168 | alındı |
| U | 2020-21 | 185 | alındı |
| U | 2021-22 | 189 | alındı |
| U | 2022-23 | 195 | alındı |
| U | 2023-24 | 195 | alındı |
| U | 2024-25 | 196 | alındı |
| U | 2025-26 | 195 | alındı |
| NBA | 2014-15 | 1311 | alındı |
| NBA | 2015-16 | 1316 | alındı |
| NBA | 2016-17 | 765 | kısmi |
| NBA | 2017-18 | 0 | alınamadı |
| NBA | 2018-19 | 0 | alınamadı |
| NBA | 2019-20 | 0 | alınamadı |
| NBA | 2020-21 | 0 | alınamadı |
| NBA | 2021-22 | 0 | alınamadı |
| NBA | 2022-23 | 0 | alınamadı |
| NBA | 2023-24 | 0 | alınamadı |
| NBA | 2024-25 | 0 | alınamadı |
| NBA | 2025-26 | 0 | alınamadı |

Oynanmayan maçlar alınmadı. EuroCup iki ayaklı eşleşme beraberlikleri dışlandı; adetler toplama.json / excluded_ties alanında. Pandemi sezonları eksik kalmıştır.

## Kaynak erişimi ve oranlar

| lig | sezon | hata |
| --- | --- | --- |
| NBA | 2016-17 | ?nbellekte HTTP 429: https://www.basketball-reference.com/leagues/NBA_2017_games-march.html; HTTP 429 sonras? bu oturumda kaynak durduruldu: https://www.basketball-reference.com/leagues/NBA_2017_games-may.html; HTTP 429 sonras? bu oturumda kaynak durduruldu: https://www.basketball-reference.com/leagues/NBA_2017_games-november.html; HTTP 429 sonras? bu oturumda kaynak durduruldu: https://www.basketball-reference.com/leagues/NBA_2017_games-october.html |
| NBA | 2017-18 | ?nbellekte HTTP 429: https://www.basketball-reference.com/leagues/NBA_2018_games.html |
| NBA | 2018-19 | ?nbellekte HTTP 429: https://www.basketball-reference.com/leagues/NBA_2019_games.html |
| NBA | 2019-20 | ?nbellekte HTTP 429: https://www.basketball-reference.com/leagues/NBA_2020_games.html |
| NBA | 2020-21 | ?nbellekte HTTP 429: https://www.basketball-reference.com/leagues/NBA_2021_games.html |
| NBA | 2021-22 | ?nbellekte HTTP 429: https://www.basketball-reference.com/leagues/NBA_2022_games.html |
| NBA | 2022-23 | ?nbellekte HTTP 429: https://www.basketball-reference.com/leagues/NBA_2023_games.html |
| NBA | 2023-24 | ?nbellekte HTTP 429: https://www.basketball-reference.com/leagues/NBA_2024_games.html |
| NBA | 2024-25 | ?nbellekte HTTP 429: https://www.basketball-reference.com/leagues/NBA_2025_games.html |
| NBA | 2025-26 | ?nbellekte HTTP 429: https://www.basketball-reference.com/leagues/NBA_2026_games.html |

Eksik oran sezonları ve kaynak mesajları:

| sezon | status | error |
| --- | --- | --- |
| 2014-15 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2014-15/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2014-15/ |
| 2015-16 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2015-16/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2015-16/ |
| 2016-17 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2016-17/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2016-17/ |
| 2017-18 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2017-18/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2017-18/ |
| 2018-19 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2018-19/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2018-19/ |
| 2019-20 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2019-20/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2019-20/ |
| 2020-21 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2020-21/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2020-21/ |
| 2021-22 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2021-22/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2021-22/ |
| 2022-23 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2022-23/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2022-23/ |
| 2023-24 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2023-24/ |
| 2024-25 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2024-25/ |
| 2025-26 | missing | Ar?iv yok; canonical=https://www.sportsbookreviewsonline.com/; https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-2025-26/ |

NBA piyasa kıyası, eğitimde avantaj eşiği seçimi ve gerçek bahis simülasyonu: **yapılmadı (kapanış oranı yok)**. ROI / maksimum düşüş / bahis sayısı hesaplanamadı. Sabit %1 güncel sermaye payı ve çeyrek Kelly çekirdeği test edildi; gerçek kazanç kanıtı değildir.

Eşleşmeyen oran satırı sayısı: **hesaplanamadı (oran satırı alınamadı)**. Açık franchise eşlemesi src/bbtahmin/veri/teams.py içinde. HTTP 200 ile ana sayfa dönen arşiv yanıtları geçerli oran verisi sayılmadı.

## Yöntem ve belirsizlik

Sezon başlangıcında yeniden eğitim; test sırasında yalnız önceki günlerin özellik durumu güncellenir. Son eğitim sezonu doğrulama, daha eski sezonlar iç eğitimdir. Elo K, ev avantajı, sezon çekmesi, EWMA, lojistik C, boosting yaprak sayısı ve Ridge alpha yalnız bu eğitim penceresinde ızgara ile seçilir. Platt kalibrasyonu önceki sezonda, o sezonu görmeyen model tahminlerinden öğrenilir. Aynı UTC gününün sonuçları birlikte geciktirilir. Izgaralar önceden tanımlıdır; geniş kapsamlı hiperparametre optimizasyonu yapılmadı.

Model − Elo log loss farkı: negatif daha iyi. Sezonlara eşit ağırlık; 10.000 sezon bootstrap örneğiyle %95 aralık ve 10.000 işaret permütasyonuyla iki yönlü p. Karşılaştırmalara Holm düzeltmesi. Az sezon ve sezonlar arası bağımlılık nedeniyle sonuç keşifseldir; p<0,05 olmadan üstünlük iddiası yok. NBA tek test sezonuna sahip olduğu için anlamlılık hesabı yapılmadı.

| lig | model | seasons | mean_season_logloss_delta | ci_low | ci_high | p | p_holm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E | logistic | 17 | -0.0059 | -0.0095 | -0.0019 | 0.0105 | 0.0420 |
| E | hist_gradient_boosting | 17 | 0.0056 | 0.0013 | 0.0100 | 0.0231 | 0.0693 |
| E | mov_elo | 17 | -0.0054 | -0.0082 | -0.0026 | 0.0018 | 0.0108 |
| U | logistic | 17 | 0.0250 | -0.0070 | 0.0772 | 0.4302 | 0.4302 |
| U | hist_gradient_boosting | 17 | 0.0079 | -0.0012 | 0.0179 | 0.1449 | 0.2898 |
| U | mov_elo | 17 | -0.0047 | -0.0076 | -0.0017 | 0.0079 | 0.0395 |

Regresyon artıklarının normal dağılım sınaması, çarpıklık, basıklık ve sigma: parametreler.json. Normal varsayımı reddedilirse handikap olasılığı doğrulanmış kabul edilmez. Gerçek handikap ve toplam skor çizgileri yok; alt/üst bahisleri değerlendirilmedi.

Veri: 12344 satır; yinelenen maç: 0. Eksik alanlar profil.json içinde. NBA ilk yarı ve tarafsız saha bilgisi yok; özellikte ev avantajı var kabul edildi. Avrupa yorgunluğu yalnız Avrupa maçlarından; yerel lig verisi yok.

Öneri: sezonlar arasındaki tutarlılığı ve kalibrasyonu birlikte değerlendirin. Eksik oranlarla bahis kararı çıkarılamaz. Kapanış oranı sağlanınca yeni zaman ayrımlı doğrulama yapılmalı. Demografik veri yok; demografik adalet iddiası yapılmadı.

## PLAN.md farkları ve yapılmayanlar

- Paket: görev kök bbtahmin/ diyor; PLAN önceliğiyle src/bbtahmin/ kullanıldı.
- İstek sınırı görevde 15, PLAN içinde 20/dk; daha sıkı 15 sınırı ikisini karşılar.
- PLAN oran kaynağını 200 olarak tanımlar; çalışmada 200 ana sayfa içeriği, arşiv değil. NBA sonradan 429 verdi.
- Sistem Python yolu Access is denied: proje içi resmi taşınabilir CPython 3.12.10 ile virtualenv üzerinden .venv kuruldu.
- BasketbolBet referansı yok; karşılaştırma yapılmadı. Formül uydurulmadı, kod kopyalanmadı.
- Yerel lig toplayıcıları yapılmadı: kaynak yok.
- Oran ayrıştırma/birleştirme ve eğitimde bahis eşiği seçimi yapılmadı: arşiv yok.
- Tahmin komutu seçilmiş saf Elo verir; sınıflandırıcı gelecek maç servisi yapılmadı.

## Referans ve test kanıtları

data/raw/basketbolbet/main.py ve data/raw altındaki benzer referans klasörleri bulunamadı; gerçek referans yolu yok. Ignore doğrulaması: .gitignore:1:data/raw/ data/raw/basketbolbet/main.py. Ayrıntı: kanit/ortam.txt.

Normal test sonucu: kanit/pytest.txt ve pytest.xml. Kasıtlı sızıntılı negatif kontrol ayrı koşuda başarısız olmalıdır: kanit/negatif_kontrol.txt. Bu beklenen başarısızlık, gerçek test paketinde kalan hata değildir.

## Tekrarlanabilirlik

kanit/: metrikler.csv, toplam.csv, tahminler.csv, kalibrasyon.csv, anlamlilik.csv, parametreler.json, profil.json, mac_sayilari.csv, mac_sayilari_tam.csv, toplama.json. Kalibrasyon PNG: docs/. Ham yanıtlar ve HTTP meta verileri: git dışı data/raw/. Gerçek pip freeze: requirements-lock.txt. Commit/merge yapılmadı.

## Test sonucu

Pytest: 34 test; 0 başarısız, 0 hata. Ayrı negatif kontrol: 1 beklenen başarısızlık (sızıntı yakalandı).

## Kalibrasyon görselleri

![E kalibrasyon](kalibrasyon_E.png)

![NBA kalibrasyon](kalibrasyon_NBA.png)

![U kalibrasyon](kalibrasyon_U.png)

## Ek keşif ve hata analizi

Lig-sezon skor dağılımları ve ev galibiyet oranı: kanit/dagilimlar.csv. Korelasyon: kanit/korelasyon.csv. IQR ile işaretlenen aykırılar: kanit/aykirilar.csv (silinmedi). Ev/deplasman favorisi alt gruplarında hata ölçümleri: kanit/hata_analizi.csv. Bunlar tanımlayıcıdır; eğitim/test ayırımı için kullanılmadı.

NBA kısmi sezonunun ayları ardışık değildir; o sezonun özellik geçmişi de eksiktir. Bu koşul hem tahmin zorluğunu hem örneklem dağılımını değiştirir.

Kalibrasyon cezalandırılmamış Platt; boosting yaprak/regularizasyon/ağaç sayısı adayları ve seçilenleri parametreler.json içindedir. Özellik döngüsü optimizasyonunun 750 gerçek satırda birebir eşdeğerlik kanıtı: kanit/ozellik_esdegerlik.json.


MOV tanımı, [FiveThirtyEight'in resmi NBA Elo açıklamasına](https://fivethirtyeight.com/features/how-we-calculate-nba-elo-ratings/) dayanır: (kazananın sayı farkı + 3)^0,8 / (7,5 + 0,006 × kazanan yönündeki maç öncesi Elo farkı). Ev avantajı bu farka dahil edilir. Yayımlanmış formül sabitleri kullanılır; K, ev avantajı ve sezon çekmesi eğitimde seçilir. Formül için sayısal birim testi vardır.


## Model seçim kararı

PLAN koşulu: yeni model, ev sahibi ve saf Elo tabanlarını hem log loss hem Brier ile geçmeli. Bu tablo gözlenen farkı ve sezon bazında istatistiksel desteği ayırır. Test sonuçlarına bakarak yeni hiperparametre ayarlanmadı.

| lig | model | logloss_delta_vs_elo | brier_delta_vs_elo | both_baselines | statistical_support |
| --- | --- | --- | --- | --- | --- |
| E | logistic | -0.0051 | -0.0020 | evet | evet |
| E | hist_gradient_boosting | 0.0055 | 0.0023 | hayır | kanıt yok / yetersiz sezon |
| NBA | logistic | -0.0086 | -0.0042 | evet | kanıt yok / yetersiz sezon |
| NBA | hist_gradient_boosting | -0.0067 | -0.0036 | evet | kanıt yok / yetersiz sezon |
| U | logistic | 0.0460 | 0.0061 | hayır | kanıt yok / yetersiz sezon |
| U | hist_gradient_boosting | 0.0100 | 0.0042 | hayır | kanıt yok / yetersiz sezon |

Taban çizgisini geçmeyen modeller önerilmez. Küçük gözlenen fark tek başına üretim kararı değildir. Tahmin komutu doğrulanmış parametrelerle saf Elo referansını sunar; sınıflandırıcılar araştırma karşılaştırmasıdır.
