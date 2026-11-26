"""Replay a prior for newly promoted Premier League clubs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import skellam

from bbtahmin.experiment_metrics import metrics, paired
from bbtahmin.football.challenger import fit
from bbtahmin.football.data import load
from bbtahmin.prospective import prediction_fingerprint


YEARS = tuple(range(2021, 2027))
FADE_MATCHES = 8
PSEUDO_GOALS = 16
MIN_CHAMPIONSHIP_GAMES = 40
FORM_SHRINKAGE_GAMES = 16
TRANSFER_PENALTY = 16
MAX_TRANSFER_SLOPE = .5
THRESHOLD = .65


def season(year):
    return f"{year}-{(year + 1) % 100:02d}"


def appearances(frame):
    return Counter(frame["home"]) + Counter(frame["away"])


def promoted_candidates(frame, year):
    """Identify eligible clubs without reading the target season's results."""
    prior = frame[(frame["season"] == season(year - 1)) &
                  (frame["date"] < f"{year}-07-01") & (frame["status"] == "final")]
    upper = appearances(prior[prior["league"] == "EN1"])
    if sum(upper.values()) != 2 * 380 or len(upper) != 20:
        raise ValueError("Complete preceding Premier League season required")
    lower = appearances(prior[prior["league"] == "EN2"])
    candidates = {team for team, games in lower.items() if games >= MIN_CHAMPIONSHIP_GAMES and team not in upper}
    games = prior[prior["league"] == "EN2"]
    margins = games["home_goals"] - games["away_goals"]
    home = margins.groupby(games["home"]).sum()
    away = (-margins).groupby(games["away"]).sum()
    return {
        team: float(home.get(team, 0) + away.get(team, 0)) / (lower[team] + FORM_SHRINKAGE_GAMES)
        for team in candidates
    }


def strength_ratio(rows):
    """Shrink actual-to-expected goal ratios toward the original model."""
    scored = conceded = expected_scored = expected_conceded = 0.
    for row in rows:
        home, away = row["home_weight"], row["away_weight"]
        if home > 0 and not row["away_promoted"]:
            scored += home * row["home_goals"]
            conceded += home * row["away_goals"]
            expected_scored += home * row["expected_home"]
            expected_conceded += home * row["expected_away"]
        if away > 0 and not row["home_promoted"]:
            scored += away * row["away_goals"]
            conceded += away * row["home_goals"]
            expected_scored += away * row["expected_away"]
            expected_conceded += away * row["expected_home"]
    if min(expected_scored, expected_conceded) <= 0:
        raise ValueError("Need earlier promoted club results against incumbent clubs")
    return ((scored + PSEUDO_GOALS) / (expected_scored + PSEUDO_GOALS),
            (conceded + PSEUDO_GOALS) / (expected_conceded + PSEUDO_GOALS))


def rates(rows, attack, defence, slope, center):
    home = np.array([row["home_weight"] for row in rows])
    away = np.array([row["away_weight"] for row in rows])
    differential = slope * (home * (np.array([row["home_form"] for row in rows]) - center)
                            - away * (np.array([row["away_form"] for row in rows]) - center))
    lh = np.array([row["expected_home"] for row in rows]) * attack**home * defence**away * np.exp(differential)
    la = np.array([row["expected_away"] for row in rows]) * attack**away * defence**home * np.exp(-differential)
    return np.clip(lh, .1, 6), np.clip(la, .1, 6)


def predict(rows, attack, defence, slope=0., center=0.):
    lh, la = rates(rows, attack, defence, slope, center)
    return np.column_stack((skellam.sf(0, lh, la), skellam.pmf(0, lh, la), skellam.cdf(-1, lh, la)))


def learn_transfer(rows, attack, defence):
    # Fit one symmetric strength slope only on earlier, affected fixtures.
    rows = [row for row in rows if row["home_weight"] or row["away_weight"]]
    forms = [row[f"{side}_form"] for row in rows for side in ("home", "away") if row[f"{side}_weight"]]
    center = float(np.mean(forms))
    h = np.array([row["home_goals"] for row in rows])
    a = np.array([row["away_goals"] for row in rows])

    def objective(slope):
        lh, la = rates(rows, attack, defence, slope, center)
        return float((lh - h * np.log(lh) + la - a * np.log(la)).sum() + TRANSFER_PENALTY * slope**2)

    result = minimize_scalar(objective, bounds=(0., MAX_TRANSFER_SLOPE), method="bounded")
    if not result.success:
        raise ValueError("Championship strength transfer fit failed")
    return float(result.x), center


def replay(frame, year):
    candidates = promoted_candidates(frame, year)
    target = frame[(frame["season"] == season(year)) &
                   (frame["league"] == "EN1") & (frame["status"] == "final")]
    rows = []
    for month, group in target.sort_values(["date", "event_id"]).groupby(target["date"].str[:7]):
        cutoff = month + "-01"
        model = fit(frame, "EN1", cutoff, "opponent")
        known = appearances(target[target["date"] < cutoff])

        def weight(team):
            return max(0, 1 - known[team] / FADE_MATCHES) if team in candidates else 0

        for game in group.itertuples():
            result = model.predict(game.home, game.away)
            rows.append(dict(
                event_id=game.event_id, day=game.date,
                y=0 if game.home_goals > game.away_goals else 2 if game.home_goals < game.away_goals else 1,
                home_goals=int(game.home_goals), away_goals=int(game.away_goals),
                home_weight=weight(game.home), away_weight=weight(game.away),
                home_promoted=game.home in candidates, away_promoted=game.away in candidates,
                home_form=candidates.get(game.home, 0.), away_form=candidates.get(game.away, 0.),
                expected_home=result["expected_home_goals"], expected_away=result["expected_away_goals"],
                p=[result["probabilities"][key] for key in ("home", "draw", "away")],
                eligible=not result["issues"],
            ))
    if not rows or len({row["event_id"] for row in rows}) != len(rows):
        raise ValueError("Need distinct observed target fixtures")
    return rows


def compare(rows, candidate):
    paired_rows = [dict(row, variant="reference") for row in rows]
    paired_rows.extend(dict(row, p=p.tolist(), variant="candidate") for row, p in zip(rows, candidate, strict=True))
    comparison = paired(paired_rows, "reference", "candidate", replicates=2000)
    for variant in ("reference", "candidate"):
        records = [row for row in paired_rows if row["variant"] == variant]
        comparison[variant] = metrics([row["y"] for row in records], [row["p"] for row in records],
                                      [row["eligible"] and max(row["p"]) >= THRESHOLD for row in records])
    return comparison


def evaluate():
    inputs = {
        p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(Path("data/football").rglob("*.json.gz")) if p.name.startswith(("EN1_", "EN2_"))
    }
    reviews = Path("data/football/fixture_reviews.json")
    inputs[reviews.as_posix()] = hashlib.sha256(reviews.read_bytes()).hexdigest()
    frame = load()
    history = {year: replay(frame, year) for year in YEARS}
    seasons = {}
    for year in YEARS[3:]:
        prior_years = range(year - 3, year)
        prior = [row for earlier in prior_years for row in history[earlier]]
        target = history[year]
        if max(row["day"] for row in prior) >= min(row["day"] for row in target):
            raise ValueError("The promoted-club prior must precede every target fixture")
        attack, defence = strength_ratio(prior)
        slope, center = learn_transfer(prior, attack, defence)
        if not np.allclose(predict(target, 1, 1), [row["p"] for row in target], atol=1e-12, rtol=0):
            raise ValueError("Neutral prior does not reproduce the production reference")
        affected = [row for row in target if row["home_weight"] or row["away_weight"]]
        days = sorted({row["day"] for row in affected})
        boundary = days[len(days) // 2]
        seasons[season(year)] = {
            "prior_seasons": [season(y) for y in prior_years],
            "attack_multiplier": attack, "defence_multiplier": defence,
            "championship_form_slope": slope, "championship_form_center": center,
            "second_period_start": boundary,
            "groups": {
                name: {
                    "common_prior": compare(rows, predict(rows, attack, defence)),
                    "club_transfer": compare(rows, predict(rows, attack, defence, slope, center)),
                }
                for name, rows in (
                    ("all", target), ("affected", affected),
                    ("earlier", [row for row in affected if row["day"] < boundary]),
                    ("later", [row for row in affected if row["day"] >= boundary]),
                )
            },
        }
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest for path, digest in inputs.items()):
        raise ValueError("English league archives changed during evaluation")
    return {
        "evidence_kind": "exploratory_retrospective",
        "fade_matches": FADE_MATCHES, "pseudo_goals": PSEUDO_GOALS,
        "minimum_prior_championship_matches": MIN_CHAMPIONSHIP_GAMES,
        "form_shrinkage_games": FORM_SHRINKAGE_GAMES,
        "transfer_penalty": TRANSFER_PENALTY, "max_transfer_slope": MAX_TRANSFER_SLOPE,
        "source_sha256": inputs, "prediction_code_sha256": prediction_fingerprint(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "seasons": seasons, "note": "Monthly replay in England. Historical publication availability is unverified.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(evaluate(), indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
