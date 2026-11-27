# Live forecast scorecard

Data cutoff (UTC) **2026-11-27T16:59:19.932776+00:00**.

## Definitions

- **Cohort**. One game per league and event ID, using the earliest checksum-verified frozen forecast. A timezone-aware start must be present and strictly later than the freeze. Basketball finals are joined by forecast checksum and fixture identity across saved settlement checks, including checks that reference earlier Argentina and prospective forecast records. Football uses publisher finals from the saved daily report joined to immutable forecasts by fixture identity and freeze time. Community publisher finals lack official verification. Football finals with date-only kickoff evidence and matches flagged for fixture review are excluded.
- **Cutoff**. Latest saved settlement check timestamp used, with each sport's cutoff reported separately. Basketball includes the per-record check timestamps, which can follow the report's start time.
- **Accuracy**. Fraction of games where the highest-probability class occurred. Ties break in class order.
- **Log loss**. Mean negative natural log of the realized class probability, floored at 1e-15.
- **Brier**. Mean squared error of the home-win probability for basketball, (p_home − y_home)². Football sums the squared probability errors over home, draw and away before averaging.
- **Confidence intervals**. 95% Wilson score intervals for accuracy. Log loss and Brier use the 2.5th and 97.5th percentiles of 2,000 bootstrap samples of games with replacement (NumPy default_rng seed 20261124, reset per cohort). Games are the resampling unit.
- **Always home**. Assigns probability 1 to home and 0 to every other class.
- **Expanding rate**. Per-league class counts from eligible ledger finals known strictly before each forecast was frozen. Add one prior count per class, giving a uniform forecast at cold start. Basketball uses the earliest saved final capture time. Football uses the saved report's check time because it has no per-game final observation times. All football forecasts in that single snapshot therefore receive uniform rates.
- **Market**. Use only complete decimal odds greater than 1 from the frozen prediction. Read decimal_odds by class, or oran_ev and oran_dep for basketball. Normalize reciprocals to sum to one. The market row and its companion model row cover the same odds-available games.
- **Calibration**. Group by highest forecast probability in left-closed 10 percentage-point bins, with 100% included in the last bin. Observed frequency is the fraction whose top pick occurred. Bins begin at 50% for basketball and 30% for football to cover all 1X2 favourites.

## Basketball

Ledger cutoff (UTC) **2026-11-27T16:58:15.489641+00:00**.
Class order is home, away.

| League | Forecast | n | Accuracy (95% CI) | Log loss (95% CI) | Brier (95% CI) |
|---|---|---:|---:|---:|---:|
| Total | Model | 394 | 69.0% [64.3%, 73.4%] | 0.5790 [0.5407, 0.6169] | 0.1997 [0.1834, 0.2160] |
| Total | Always home | 394 | 57.9% [52.9%, 62.6%] | 14.5519 [12.8863, 16.2174] | 0.4213 [0.3731, 0.4695] |
| Total | Expanding league rate | 394 | 55.1% [50.1%, 59.9%] | 0.7002 [0.6831, 0.7183] | 0.2528 [0.2448, 0.2612] |
| Total | Market (no market data) | 0 | — | — | — |
| ABA | Model | 41 | 68.3% [53.0%, 80.4%] | 0.5496 [0.4314, 0.6811] | 0.1889 [0.1364, 0.2476] |
| ABA | Always home | 41 | 61.0% [45.7%, 74.3%] | 13.4785 [8.4241, 18.5330] | 0.3902 [0.2439, 0.5366] |
| ABA | Expanding league rate | 41 | 61.0% [45.7%, 74.3%] | 0.6763 [0.6159, 0.7330] | 0.2416 [0.2123, 0.2692] |
| ABA | Market (no market data) | 0 | — | — | — |
| ARG_LNB | Model | 50 | 66.0% [52.2%, 77.6%] | 0.5951 [0.5153, 0.6843] | 0.2042 [0.1677, 0.2453] |
| ARG_LNB | Always home | 50 | 60.0% [46.2%, 72.4%] | 13.8155 [8.9801, 18.6509] | 0.4000 [0.2600, 0.5400] |
| ARG_LNB | Expanding league rate | 50 | 62.0% [48.2%, 74.1%] | 0.6820 [0.6455, 0.7191] | 0.2444 [0.2265, 0.2628] |
| ARG_LNB | Market (no market data) | 0 | — | — | — |
| E | Model | 72 | 58.3% [46.8%, 69.0%] | 0.6523 [0.5650, 0.7444] | 0.2330 [0.1938, 0.2751] |
| E | Always home | 72 | 54.2% [42.7%, 65.2%] | 15.8303 [11.9926, 19.6679] | 0.4583 [0.3472, 0.5694] |
| E | Expanding league rate | 72 | 54.2% [42.7%, 65.2%] | 0.6966 [0.6748, 0.7180] | 0.2517 [0.2409, 0.2622] |
| E | Market (no market data) | 0 | — | — | — |
| ECW | Model | 74 | 83.8% [73.8%, 90.5%] | 0.4636 [0.3622, 0.5722] | 0.1519 [0.1114, 0.1957] |
| ECW | Always home | 74 | 48.6% [37.6%, 59.8%] | 17.7361 [14.0022, 21.4701] | 0.5135 [0.4054, 0.6216] |
| ECW | Expanding league rate | 74 | 35.1% [25.2%, 46.5%] | 0.7532 [0.7164, 0.7887] | 0.2794 [0.2615, 0.2967] |
| ECW | Market (no market data) | 0 | — | — | — |
| FEC | Model | 96 | 72.9% [63.3%, 80.8%] | 0.5752 [0.4988, 0.6582] | 0.1959 [0.1618, 0.2320] |
| FEC | Always home | 96 | 63.5% [53.6%, 72.5%] | 12.5923 [9.3543, 16.1901] | 0.3646 [0.2708, 0.4688] |
| FEC | Expanding league rate | 96 | 62.5% [52.5%, 71.5%] | 0.6896 [0.6353, 0.7449] | 0.2458 [0.2214, 0.2703] |
| FEC | Market (no market data) | 0 | — | — | — |
| KBL | Model | 38 | 60.5% [44.7%, 74.4%] | 0.6899 [0.6107, 0.7787] | 0.2472 [0.2095, 0.2894] |
| KBL | Always home | 38 | 57.9% [42.2%, 72.1%] | 14.5426 [9.0892, 19.9961] | 0.4211 [0.2632, 0.5789] |
| KBL | Expanding league rate | 38 | 60.5% [44.7%, 74.4%] | 0.6865 [0.6500, 0.7249] | 0.2466 [0.2287, 0.2655] |
| KBL | Market (no market data) | 0 | — | — | — |
| UKR | Model | 23 | 60.9% [40.8%, 77.8%] | 0.5710 [0.4526, 0.7058] | 0.1965 [0.1418, 0.2592] |
| UKR | Always home | 23 | 65.2% [44.9%, 81.2%] | 12.0135 [6.0067, 19.5219] | 0.3478 [0.1739, 0.5652] |
| UKR | Expanding league rate | 23 | 56.5% [36.8%, 74.4%] | 0.6908 [0.6407, 0.7507] | 0.2488 [0.2242, 0.2783] |
| UKR | Market (no market data) | 0 | — | — | — |

### Model calibration

| League | Favourite probability | n | Forecast mean | Observed frequency |
|---|---|---:|---:|---:|
| Total | 50%–60% | 117 | 54.9% | 58.1% |
| Total | 60%–70% | 119 | 64.8% | 62.2% |
| Total | 70%–80% | 86 | 75.6% | 75.6% |
| Total | 80%–90% | 49 | 85.1% | 85.7% |
| Total | 90%–100% | 23 | 95.0% | 100.0% |
| ABA | 50%–60% | 10 | 55.1% | 60.0% |
| ABA | 60%–70% | 10 | 64.5% | 40.0% |
| ABA | 70%–80% | 11 | 75.8% | 72.7% |
| ABA | 80%–90% | 8 | 87.4% | 100.0% |
| ABA | 90%–100% | 2 | 94.1% | 100.0% |
| ARG_LNB | 50%–60% | 19 | 54.3% | 47.4% |
| ARG_LNB | 60%–70% | 15 | 63.9% | 66.7% |
| ARG_LNB | 70%–80% | 15 | 75.7% | 86.7% |
| ARG_LNB | 80%–90% | 1 | 82.7% | 100.0% |
| ARG_LNB | 90%–100% | 0 | — | — |
| E | 50%–60% | 19 | 55.7% | 52.6% |
| E | 60%–70% | 23 | 65.3% | 34.8% |
| E | 70%–80% | 20 | 75.0% | 75.0% |
| E | 80%–90% | 9 | 84.2% | 88.9% |
| E | 90%–100% | 1 | 92.5% | 100.0% |
| ECW | 50%–60% | 17 | 54.7% | 82.4% |
| ECW | 60%–70% | 14 | 64.4% | 78.6% |
| ECW | 70%–80% | 11 | 76.8% | 81.8% |
| ECW | 80%–90% | 16 | 85.0% | 75.0% |
| ECW | 90%–100% | 16 | 95.6% | 100.0% |
| FEC | 50%–60% | 25 | 54.6% | 64.0% |
| FEC | 60%–70% | 34 | 65.3% | 73.5% |
| FEC | 70%–80% | 21 | 76.3% | 71.4% |
| FEC | 80%–90% | 12 | 84.1% | 83.3% |
| FEC | 90%–100% | 4 | 93.5% | 100.0% |
| KBL | 50%–60% | 21 | 55.0% | 57.1% |
| KBL | 60%–70% | 12 | 63.7% | 75.0% |
| KBL | 70%–80% | 5 | 72.5% | 40.0% |
| KBL | 80%–90% | 0 | — | — |
| KBL | 90%–100% | 0 | — | — |
| UKR | 50%–60% | 6 | 55.4% | 16.7% |
| UKR | 60%–70% | 11 | 65.6% | 63.6% |
| UKR | 70%–80% | 3 | 74.1% | 100.0% |
| UKR | 80%–90% | 3 | 86.4% | 100.0% |
| UKR | 90%–100% | 0 | — | — |

## Football

Ledger cutoff (UTC) **2026-11-27T16:59:19.932776+00:00**.
Class order is home, draw, away.
Excluded 128 publisher finals without a verified kickoff timestamp.
Kickoff exclusions by league (DE1 15, EN1 16, EN2 19, ES1 7, FR1 11, IT1 27, NL1 15, PT1 13, TR1 5).

| League | Forecast | n | Accuracy (95% CI) | Log loss (95% CI) | Brier (95% CI) |
|---|---|---:|---:|---:|---:|
| Total | Model | 164 | 54.9% [47.2%, 62.3%] | 0.9866 [0.9321, 1.0454] | 0.5868 [0.5480, 0.6280] |
| Total | Always home | 164 | 44.5% [37.1%, 52.2%] | 19.1648 [16.6376, 21.9026] | 1.1098 [0.9634, 1.2683] |
| Total | Expanding league rate | 164 | 44.5% [37.1%, 52.2%] | 1.0986 [1.0986, 1.0986] | 0.6667 [0.6667, 0.6667] |
| Total | Market (no market data) | 0 | — | — | — |
| DE1 | Model | 12 | 83.3% [55.2%, 95.3%] | 0.7828 [0.5633, 1.1199] | 0.4394 [0.2822, 0.6779] |
| DE1 | Always home | 12 | 58.3% [32.0%, 80.7%] | 14.3912 [5.7565, 23.0978] | 0.8333 [0.3333, 1.3375] |
| DE1 | Expanding league rate | 12 | 58.3% [32.0%, 80.7%] | 1.0986 [1.0986, 1.0986] | 0.6667 [0.6667, 0.6667] |
| DE1 | Market (no market data) | 0 | — | — | — |
| EN1 | Model | 19 | 47.4% [27.3%, 68.3%] | 1.0494 [0.9035, 1.1964] | 0.6339 [0.5301, 0.7421] |
| EN1 | Always home | 19 | 52.6% [31.7%, 72.7%] | 16.3605 [9.0892, 23.6318] | 0.9474 [0.5263, 1.3684] |
| EN1 | Expanding league rate | 19 | 52.6% [31.7%, 72.7%] | 1.0986 [1.0986, 1.0986] | 0.6667 [0.6667, 0.6667] |
| EN1 | Market (no market data) | 0 | — | — | — |
| EN2 | Model | 52 | 51.9% [38.7%, 64.9%] | 1.0334 [0.9469, 1.1188] | 0.6188 [0.5586, 0.6810] |
| EN2 | Always home | 52 | 46.2% [33.3%, 59.5%] | 18.5978 [13.9484, 23.2473] | 1.0769 [0.8077, 1.3462] |
| EN2 | Expanding league rate | 52 | 46.2% [33.3%, 59.5%] | 1.0986 [1.0986, 1.0986] | 0.6667 [0.6667, 0.6667] |
| EN2 | Market (no market data) | 0 | — | — | — |
| ES1 | Model | 19 | 63.2% [41.0%, 80.9%] | 0.9122 [0.7591, 1.0745] | 0.5335 [0.4252, 0.6472] |
| ES1 | Always home | 19 | 42.1% [23.1%, 63.7%] | 19.9961 [12.7248, 27.2675] | 1.1579 [0.7368, 1.5789] |
| ES1 | Expanding league rate | 19 | 42.1% [23.1%, 63.7%] | 1.0986 [1.0986, 1.0986] | 0.6667 [0.6667, 0.6667] |
| ES1 | Market (no market data) | 0 | — | — | — |
| FR1 | Model | 16 | 37.5% [18.5%, 61.4%] | 1.1114 [0.9486, 1.2750] | 0.6791 [0.5637, 0.7934] |
| FR1 | Always home | 16 | 25.0% [10.2%, 49.5%] | 25.9041 [17.2694, 32.3801] | 1.5000 [1.0000, 1.8750] |
| FR1 | Expanding league rate | 16 | 25.0% [10.2%, 49.5%] | 1.0986 [1.0986, 1.0986] | 0.6667 [0.6667, 0.6667] |
| FR1 | Market (no market data) | 0 | — | — | — |
| IT1 | Model | 22 | 54.5% [34.7%, 73.1%] | 0.9602 [0.8019, 1.1267] | 0.5671 [0.4545, 0.6838] |
| IT1 | Always home | 22 | 45.5% [26.9%, 65.3%] | 18.8393 [10.9896, 25.1191] | 1.0909 [0.6364, 1.4545] |
| IT1 | Expanding league rate | 22 | 45.5% [26.9%, 65.3%] | 1.0986 [1.0986, 1.0986] | 0.6667 [0.6667, 0.6667] |
| IT1 | Market (no market data) | 0 | — | — | — |
| NL1 | Model | 20 | 55.0% [34.2%, 74.2%] | 0.9777 [0.8029, 1.1582] | 0.5823 [0.4616, 0.7053] |
| NL1 | Always home | 20 | 35.0% [18.1%, 56.7%] | 22.4502 [15.5424, 29.3580] | 1.3000 [0.9000, 1.7000] |
| NL1 | Expanding league rate | 20 | 35.0% [18.1%, 56.7%] | 1.0986 [1.0986, 1.0986] | 0.6667 [0.6667, 0.6667] |
| NL1 | Market (no market data) | 0 | — | — | — |
| PT1 | Model | 4 | 75.0% [30.1%, 95.4%] | 0.7358 [0.4301, 1.0449] | 0.4042 [0.1838, 0.6246] |
| PT1 | Always home | 4 | 75.0% [30.1%, 95.4%] | 8.6347 [0.0000, 25.9041] | 0.5000 [0.0000, 1.5000] |
| PT1 | Expanding league rate | 4 | 75.0% [30.1%, 95.4%] | 1.0986 [1.0986, 1.0986] | 0.6667 [0.6667, 0.6667] |
| PT1 | Market (no market data) | 0 | — | — | — |
| TR1 | Model | 0 | — | — | — |
| TR1 | Always home | 0 | — | — | — |
| TR1 | Expanding league rate | 0 | — | — | — |
| TR1 | Market (no market data) | 0 | — | — | — |

### Model calibration

| League | Favourite probability | n | Forecast mean | Observed frequency |
|---|---|---:|---:|---:|
| Total | 30%–40% | 27 | 38.5% | 37.0% |
| Total | 40%–50% | 78 | 44.5% | 51.3% |
| Total | 50%–60% | 38 | 54.3% | 63.2% |
| Total | 60%–70% | 16 | 64.1% | 87.5% |
| Total | 70%–80% | 3 | 70.9% | 33.3% |
| Total | 80%–90% | 2 | 82.9% | 50.0% |
| Total | 90%–100% | 0 | — | — |
| DE1 | 30%–40% | 1 | 38.9% | 0.0% |
| DE1 | 40%–50% | 3 | 47.2% | 100.0% |
| DE1 | 50%–60% | 4 | 52.1% | 100.0% |
| DE1 | 60%–70% | 3 | 66.5% | 100.0% |
| DE1 | 70%–80% | 0 | — | — |
| DE1 | 80%–90% | 1 | 84.8% | 0.0% |
| DE1 | 90%–100% | 0 | — | — |
| EN1 | 30%–40% | 1 | 39.6% | 0.0% |
| EN1 | 40%–50% | 13 | 46.1% | 53.8% |
| EN1 | 50%–60% | 4 | 53.2% | 50.0% |
| EN1 | 60%–70% | 1 | 60.6% | 0.0% |
| EN1 | 70%–80% | 0 | — | — |
| EN1 | 80%–90% | 0 | — | — |
| EN1 | 90%–100% | 0 | — | — |
| EN2 | 30%–40% | 12 | 38.2% | 33.3% |
| EN2 | 40%–50% | 25 | 44.0% | 52.0% |
| EN2 | 50%–60% | 12 | 54.5% | 66.7% |
| EN2 | 60%–70% | 2 | 62.8% | 100.0% |
| EN2 | 70%–80% | 1 | 70.1% | 0.0% |
| EN2 | 80%–90% | 0 | — | — |
| EN2 | 90%–100% | 0 | — | — |
| ES1 | 30%–40% | 4 | 38.7% | 50.0% |
| ES1 | 40%–50% | 6 | 44.0% | 50.0% |
| ES1 | 50%–60% | 6 | 54.0% | 66.7% |
| ES1 | 60%–70% | 2 | 64.7% | 100.0% |
| ES1 | 70%–80% | 1 | 72.4% | 100.0% |
| ES1 | 80%–90% | 0 | — | — |
| ES1 | 90%–100% | 0 | — | — |
| FR1 | 30%–40% | 3 | 38.4% | 33.3% |
| FR1 | 40%–50% | 8 | 44.2% | 37.5% |
| FR1 | 50%–60% | 3 | 54.7% | 33.3% |
| FR1 | 60%–70% | 2 | 63.0% | 50.0% |
| FR1 | 70%–80% | 0 | — | — |
| FR1 | 80%–90% | 0 | — | — |
| FR1 | 90%–100% | 0 | — | — |
| IT1 | 30%–40% | 3 | 38.6% | 33.3% |
| IT1 | 40%–50% | 10 | 45.1% | 50.0% |
| IT1 | 50%–60% | 6 | 55.8% | 50.0% |
| IT1 | 60%–70% | 3 | 63.5% | 100.0% |
| IT1 | 70%–80% | 0 | — | — |
| IT1 | 80%–90% | 0 | — | — |
| IT1 | 90%–100% | 0 | — | — |
| NL1 | 30%–40% | 3 | 39.2% | 66.7% |
| NL1 | 40%–50% | 11 | 43.4% | 45.5% |
| NL1 | 50%–60% | 3 | 55.2% | 66.7% |
| NL1 | 60%–70% | 1 | 63.5% | 100.0% |
| NL1 | 70%–80% | 1 | 70.2% | 0.0% |
| NL1 | 80%–90% | 1 | 81.0% | 100.0% |
| NL1 | 90%–100% | 0 | — | — |
| PT1 | 30%–40% | 0 | — | — |
| PT1 | 40%–50% | 2 | 41.9% | 50.0% |
| PT1 | 50%–60% | 0 | — | — |
| PT1 | 60%–70% | 2 | 65.1% | 100.0% |
| PT1 | 70%–80% | 0 | — | — |
| PT1 | 80%–90% | 0 | — | — |
| PT1 | 90%–100% | 0 | — | — |
| TR1 | 30%–40% | 0 | — | — |
| TR1 | 40%–50% | 0 | — | — |
| TR1 | 50%–60% | 0 | — | — |
| TR1 | 60%–70% | 0 | — | — |
| TR1 | 70%–80% | 0 | — | — |
| TR1 | 80%–90% | 0 | — | — |
| TR1 | 90%–100% | 0 | — | — |

### Model top picks and actual outcomes

| League | Class | Top pick n | Top pick rate | Actual n | Actual rate |
|---|---|---:|---:|---:|---:|
| Total | home | 105 | 64.0% | 73 | 44.5% |
| Total | draw | 0 | 0.0% | 35 | 21.3% |
| Total | away | 59 | 36.0% | 56 | 34.1% |
| DE1 | home | 9 | 75.0% | 7 | 58.3% |
| DE1 | draw | 0 | 0.0% | 1 | 8.3% |
| DE1 | away | 3 | 25.0% | 4 | 33.3% |
| EN1 | home | 13 | 68.4% | 10 | 52.6% |
| EN1 | draw | 0 | 0.0% | 5 | 26.3% |
| EN1 | away | 6 | 31.6% | 4 | 21.1% |
| EN2 | home | 31 | 59.6% | 24 | 46.2% |
| EN2 | draw | 0 | 0.0% | 12 | 23.1% |
| EN2 | away | 21 | 40.4% | 16 | 30.8% |
| ES1 | home | 11 | 57.9% | 8 | 42.1% |
| ES1 | draw | 0 | 0.0% | 5 | 26.3% |
| ES1 | away | 8 | 42.1% | 6 | 31.6% |
| FR1 | home | 14 | 87.5% | 4 | 25.0% |
| FR1 | draw | 0 | 0.0% | 3 | 18.8% |
| FR1 | away | 2 | 12.5% | 9 | 56.2% |
| IT1 | home | 11 | 50.0% | 10 | 45.5% |
| IT1 | draw | 0 | 0.0% | 5 | 22.7% |
| IT1 | away | 11 | 50.0% | 7 | 31.8% |
| NL1 | home | 12 | 60.0% | 7 | 35.0% |
| NL1 | draw | 0 | 0.0% | 3 | 15.0% |
| NL1 | away | 8 | 40.0% | 10 | 50.0% |
| PT1 | home | 4 | 100.0% | 3 | 75.0% |
| PT1 | draw | 0 | 0.0% | 1 | 25.0% |
| PT1 | away | 0 | 0.0% | 0 | 0.0% |
| TR1 | home | 0 | — | 0 | — |
| TR1 | draw | 0 | — | 0 | — |
| TR1 | away | 0 | — | 0 | — |
