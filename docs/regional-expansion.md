# Regional data and prediction expansion — 23 October 2026

The application previously could not generate a trained ABA prediction for the user's Cluj–Studentski Centar screenshot. This release adds a separate official ABA archive/model and connects two existing European cup models to the daily application.

## Numeric data additions

| Archive | Before | After | Added | Source / coverage |
|---|---:|---:|---:|---|
| Senior ABA | 0 | 3,023 | 3,023 | Official season calendars, 2010–11 through partial 2026–27; 39 observed identities |
| EuroCup Women | 674 | 678 | 4 | Official FIBA pages; separately stored women |
| FIBA Europe Cup men | 651 | 651 | 0 | Refreshed fixture/capture provenance; separately stored men |

The core 54,808-game and separate 12,850-game Asian archives are unchanged. These counts must not be added to auxiliary club observations without deduplicating cross-archive games. No completeness guarantee is inferred from counts. All source URLs, per-season counts, missing rows and collection errors are in `kanit/competitions/ABA_collection.json`.

## Fixed model policy and results

ABA uses separate fitted weights. Earlier seasons train Ridge score/total regressions and logistic regression; Elo is also evaluated. The preceding season's first UTC-day half calibrates the score scale, and its second half selects the lowest-log-loss candidate among score, logistic, Elo and their equal ensemble. The target season never chooses its own model. Features update only after the UTC day ends. Training labels and odds are not mixed into each other.

| Same 2,623 completed-season test games | Correct | Accuracy | Log loss |
|---|---:|---:|---:|
| Always nominal home | 1,660 | 63.29% | — |
| Elo | 1,918 | 73.12% | 0.55022 |
| Score model | 1,933 | 73.69% | 0.52594 |
| Previous-season policy (runtime) | 1,922 | 73.27% | 0.52567 |

The runtime policy has slightly better log loss than the fixed score model but **lower winner accuracy**. Its accuracy exceeds Elo by only 4/2,623 games (0.15 percentage points). This is not evidence of a general accuracy improvement across the project. Retrospectively collected data does not prove publication-time availability.

Runtime-policy team-score MAE is **8.14 points**, total MAE **13.60**, margin MAE **8.85**; the nominal 80% total interval covers **79.64%** of these completed-season games. Current partial 2026–27: **20/31 (64.52%)**; keep this small cohort separate. All candidate outcomes and folds are preserved in `kanit/regional_models`, including the higher-current-accuracy Elo comparator.

## Real prospective run

```bash
python -m bbtahmin gunluk --ligler ABA ECW FEC --saat 168 --cikti docs/kanit/regional_runtime --json
```

At 2026-10-23 13:18 UTC, this froze **58 new future fixtures**: ABA 9, ECW 25, FEC 24. **11** passed the 65% probability filter and diagnostic data gate; that filter is not measured recommendation accuracy. **0 settled / 58 pending**, so prospective accuracy is unavailable. A repeat run reused the original immutable predictions. The original two EuroLeague records are untouched.

Cluj–SC Derby is now a genuine model forecast: **88.93–81.41**, home win **73.48%**, total **170.33**. This differs from the earlier manual 94–82 conversation estimate, which must remain labeled manual. The new model forecast is independently frozen before the scheduled 15:00 UTC tipoff; neither replaces the other in retrospective evaluation.

## Scope and reproducibility

The daily CLI and local application grow from 5 to **8 competitions**. ABA team aliases support Cluj Napoca and Studentski Centar/SC Derby. The bulletin explicitly maps only senior ABA/group A/group B; ABA 2 and U19 remain unsupported. MCP coverage exposes the new archive.

```bash
python -m bbtahmin aba-topla --baslangic 2010
PYTHONPATH=src python scripts/evaluate_regional.py
python -m bbtahmin gunluk --guncelle
python -m bbtahmin app
```

Only prior-UTC-day ABA calendar scores enter training/settlement, since the calendar has no reliable same-day final flag. This can delay automatic settlement. Official CET-labeled clocks use Europe/Belgrade daylight saving, and TBA/playoff placeholders are excluded. Conflicting persisted results reject the refresh. Ukraine, Sweden and Turkey are not yet trained daily competitions; their screenshot market commentary is not converted into fabricated model output.
