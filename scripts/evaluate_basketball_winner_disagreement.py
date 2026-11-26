"""Replay a winner override when basketball probabilities and margins disagree."""
import argparse
import hashlib
import json
from pathlib import Path

from threadpoolctl import threadpool_limits

from bbtahmin.asia_model import fit_fold
from bbtahmin.experiment_metrics import metrics, paired
from bbtahmin.ozellik import build_features
from bbtahmin.prospective import prediction_fingerprint
from bbtahmin.shadow_models import FORFEIT_GAMES
from scripts.evaluate_basketball_logit_blend import LEAGUES, SEASONS
from scripts.evaluate_improvement_basketball import load


MIN_DISAGREEMENTS = 20
REFERENCE = "reference"
SWITCH = "switch"
GATED = "prior_selected"


def choices(reference, score):
    """Return both two-class distributions with the same away/home tie rule."""
    disagreement = (reference > .5) != (score > .5)
    return disagreement, {REFERENCE: [1 - reference, reference],
                          SWITCH: [1 - score, score] if disagreement else [1 - reference, reference]}


def replay(games, league):
    features = build_features(games)
    seasons = {}
    for season in SEASONS:
        target = games.loc[games["sezon"].eq(season)]
        previous = games.loc[games["sezon"].lt(season), "tarih_utc"]
        if target.empty or previous.empty or previous.max() >= target["tarih_utc"].min():
            raise ValueError(f"Strict previous-season data required in {league} {season}")
        probabilities, _, _, policy = fit_fold(games, features, season)
        rows = []
        for g, reference, score in zip(target.itertuples(), probabilities[policy["selected"]],
                                       probabilities["score"], strict=True):
            disagreement, compared = choices(float(reference), float(score))
            rows.extend(dict(event_id=f"{league}:{g.mac_id}", day=g.tarih_utc.strftime("%Y-%m-%d"),
                             y=int(g.ev_skor > g.dep_skor), variant=name, p=p, disagreement=disagreement)
                        for name, p in compared.items())
        seasons[season] = dict(learner=policy["selected"], rows=rows)
    return seasons


def summary(rows, variant):
    p = [r["p"] for r in rows if r["variant"] == variant]
    y = [r["y"] for r in rows if r["variant"] == variant]
    return metrics(y, p, [max(v) >= .65 for v in p])


def prior_decision(prior, target):
    if max(r["day"] for r in prior) >= min(r["day"] for r in target):
        raise ValueError("The override choice must precede all target fixtures")
    disagreements = [row for row in prior if row["disagreement"]]
    n = len(disagreements) // 2
    if n < MIN_DISAGREEMENTS:
        return dict(prior_disagreements=n, use_score=False, reason="insufficient_prior_disagreements")
    ref = summary(disagreements, REFERENCE)["all"]
    alt = summary(disagreements, SWITCH)["all"]
    allowed = (alt["accuracy"] >= ref["accuracy"] + .01 and alt["log_loss"] <= ref["log_loss"] - .005
               and alt["brier"] <= ref["brier"])
    return dict(prior_disagreements=n, use_score=allowed, reference=ref, score=alt)


def summarize(rows):
    results = {name: summary(rows, name) for name in (REFERENCE, SWITCH, GATED)}
    results["paired"] = {name: paired(rows, REFERENCE, name, replicates=2000) for name in (SWITCH, GATED)}
    results["disagreements"] = sum(r["variant"] == REFERENCE and r["disagreement"] for r in rows)
    return results


def evaluate():
    leagues = {}
    pooled = {s: [] for s in SEASONS[1:]}
    for league in LEAGUES:
        games, hashes = load(league)
        games = games.loc[~games["mac_id"].isin(FORFEIT_GAMES)].reset_index(drop=True)
        seasons = replay(games, league)
        results = {}
        for prior, target in zip(SEASONS[:-1], SEASONS[1:], strict=True):
            rows = seasons[target]["rows"]
            decision = prior_decision(seasons[prior]["rows"], rows)
            keep = SWITCH if decision["use_score"] else REFERENCE
            comparison = rows + [dict(r, variant=GATED) for r in rows if r["variant"] == keep]
            results[target] = dict(decision=decision, reference_learner=seasons[target]["learner"],
                                   results=summarize(comparison))
            pooled[target].extend(comparison)
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest for p, digest in hashes.items()):
            raise ValueError("Archives changed during evaluation")
        leagues[league] = dict(input_sha256=hashes, seasons=results)
    report = {}
    for season, rows in pooled.items():
        days = sorted({r["day"] for r in rows})
        boundary = days[len(days) // 2]
        report[season] = dict(all=summarize(rows),
                              earlier=summarize([r for r in rows if r["day"] < boundary]),
                              later=summarize([r for r in rows if r["day"] >= boundary]),
                              second_period_start=boundary)
    return dict(evidence_kind="exploratory_retrospective", leagues=leagues, pooled=report,
                minimum_prior_disagreements=MIN_DISAGREEMENTS, prediction_code_sha256=prediction_fingerprint(),
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                note="Common historical learner policy, with unknown point-in-time publication availability.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        report = evaluate()
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
