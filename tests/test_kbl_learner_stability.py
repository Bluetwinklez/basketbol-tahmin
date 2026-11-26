import numpy as np
import pandas as pd
import pytest

from scripts.evaluate_basketball_logit_blend import CANDIDATE, build
from scripts.evaluate_kbl_learner_stability import build_target


def fixtures():
    rows = []
    for year in range(2022, 2026):
        for i in range(52):
            y = i % 2
            for variant, strength in {"score": .72, "logistic": .44, "elo": .60,
                                      "ensemble": .59, "selected_policy": .60}.items():
                rows.append(dict(
                    mac_id=f"{year}-{i}", sezon=f"{year}-{(year+1)%100:02}",
                    tarih_utc=pd.Timestamp(f"{year}-10-01", tz="UTC") + pd.Timedelta(days=i // 4),
                    y=y, variant=variant, p=strength if y else 1 - strength,
                ))
    return pd.DataFrame(rows)


def test_kbl_weights_use_earlier_predictions_only():
    rows = fixtures()
    spec, _ = build_target(rows, "2025-26")
    target = rows["sezon"].eq("2025-26")
    rows.loc[target, "y"] = 1 - rows.loc[target, "y"]
    changed, _ = build_target(rows, "2025-26")
    assert changed == spec
    assert spec["prior_seasons"] == ["2022-23", "2023-24", "2024-25"]
    assert spec["weights"]["score"] > spec["weights"]["logistic"]
    np.testing.assert_allclose(sum(spec["weights"].values()), 1)


def test_kbl_rejects_prior_season_label_with_target_date():
    rows = fixtures()
    rows.loc[rows["mac_id"].eq("2024-1"), "tarih_utc"] = pd.Timestamp("2025-12-01", tz="UTC")
    with pytest.raises(ValueError, match="must precede"):
        build_target(rows, "2025-26")


def test_regularized_basketball_blend_fixes_target_probabilities_before_outcomes():
    rows = fixtures()
    spec, result = build(rows, "2025-26", "KBL")
    target = rows["sezon"].eq("2025-26")
    rows.loc[target, "y"] = 1 - rows.loc[target, "y"]
    changed, again = build(rows, "2025-26", "KBL")
    assert changed == spec
    old = [(r["event_id"], r["p"]) for r in result if r["variant"] == CANDIDATE]
    new = [(r["event_id"], r["p"]) for r in again if r["variant"] == CANDIDATE]
    assert len(old) == len(new) == 52
    assert old == new
