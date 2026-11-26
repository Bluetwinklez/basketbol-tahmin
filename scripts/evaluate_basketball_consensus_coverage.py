"""Replay basketball forecast selection at equal daily coverage."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from bbtahmin.asia_model import fit_fold
from bbtahmin.ozellik import build_features
from bbtahmin.prospective import prediction_fingerprint
from bbtahmin.shadow_models import FORFEIT_GAMES
from scripts.evaluate_basketball_logit_blend import LEAGUES, SEASONS
from scripts.evaluate_improvement_basketball import load
from scripts.evaluate_kbl_learner_stability import LEARNERS


THRESHOLD = 0.65
REPLICATES = 2000
SEED = 20261126


def select(games, probabilities, learner):
    """Rank the same picks using pregame probabilities, with equal daily slots."""
    frame = games[["mac_id", "tarih_utc", "ev_skor", "dep_skor"]].reset_index(drop=True).copy()
    reference = np.asarray(probabilities[learner], dtype=float)
    sources = np.column_stack([probabilities[name] for name in LEARNERS])
    if len(reference) != len(frame) or len(sources) != len(frame) or frame["mac_id"].duplicated().any():
        raise ValueError("One set of learner probabilities per distinct fixture is required")
    values = np.column_stack([reference, sources])
    if not np.isfinite(values).all() or not ((values >= 0) & (values <= 1)).all():
        raise ValueError("Invalid learner probability")
    home_pick = reference > 0.5
    support = np.where(home_pick[:, None], sources, 1 - sources).min(axis=1)
    frame["day"] = frame["tarih_utc"].dt.strftime("%Y-%m-%d")
    frame["confidence"] = np.maximum(reference, 1 - reference)
    frame["support"] = support
    frame["reference"] = frame["confidence"] >= THRESHOLD
    frame["candidate"] = False
    for _, daily in frame.groupby("day", sort=False):
        slots = int(daily["reference"].sum())
        selected = daily.sort_values(["support", "confidence", "mac_id"], ascending=[False, False, True]).head(slots)
        frame.loc[selected.index, "candidate"] = True
    frame["correct"] = home_pick == (frame["ev_skor"] > frame["dep_skor"]).to_numpy()
    return frame


def summarize(frame):
    count = int(frame["reference"].sum())
    if count != int(frame["candidate"].sum()):
        raise ValueError("The two selection rules must have the same coverage")
    added = frame["candidate"] & ~frame["reference"]
    removed = frame["reference"] & ~frame["candidate"]
    change = (added.astype(int) - removed.astype(int)) * frame["correct"].astype(int)
    blocks = pd.DataFrame({"day": frame["day"], "selected": frame["reference"], "change": change})
    daily = blocks.groupby("day")[["selected", "change"]].sum().to_numpy()
    interval = None
    if count:
        sampled = daily[np.random.default_rng(SEED).integers(len(daily), size=(REPLICATES, len(daily)))].sum(axis=1)
        valid = sampled[:, 0] > 0
        interval = np.quantile(sampled[valid, 1] / sampled[valid, 0], [.025, .975]).tolist()
    return dict(games=len(frame), selected=count, days=len(daily), coverage=count / len(frame),
                reference_correct=int((frame["reference"] & frame["correct"]).sum()),
                candidate_correct=int((frame["candidate"] & frame["correct"]).sum()),
                replaced=int(added.sum()), accuracy_delta=float(change.sum() / count) if count else None,
                day_block_95_interval=interval)


def periods(frame):
    days = sorted(frame["day"].unique())
    if len(days) < 2:
        raise ValueError("Two distinct test days are required")
    boundary = days[len(days) // 2]
    early = frame["day"] < boundary
    return dict(all=summarize(frame), early=summarize(frame.loc[early]),
                late=summarize(frame.loc[~early]), second_period_start=boundary)


def evaluate():
    leagues = {}
    pooled = {season: [] for season in SEASONS}
    for league in LEAGUES:
        games, hashes = load(league)
        keep = ~games["mac_id"].isin(FORFEIT_GAMES)
        games = games.loc[keep].reset_index(drop=True)
        features = build_features(games)
        seasons = {}
        for season in SEASONS:
            target = games.loc[games["sezon"].eq(season)]
            prior = games.loc[games["sezon"].lt(season), "tarih_utc"]
            if target.empty or prior.empty or prior.max() >= target["tarih_utc"].min():
                raise ValueError(f"Strict prior season training required for {league} {season}")
            probabilities, _, _, policy = fit_fold(games, features, season)
            chosen = select(target, probabilities, policy["selected"])
            seasons[season] = dict(learner=policy, **periods(chosen))
            pooled[season].append(chosen)
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in hashes.items()):
            raise ValueError(f"{league} archive changed during evaluation")
        leagues[league] = dict(seasons=seasons, input_sha256=hashes, excluded_forfeits=int((~keep).sum()))
    frames = {season: pd.concat(parts, ignore_index=True) for season, parts in pooled.items()}
    return {
        "evidence_kind": "exploratory_retrospective",
        "prediction_code_sha256": prediction_fingerprint(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "reference_threshold": THRESHOLD,
        "day_block_replicates": REPLICATES,
        "seed": SEED,
        "leagues": leagues,
        "seasons": {season: periods(frame) for season, frame in frames.items()},
        "completed": periods(pd.concat([frames[s] for s in SEASONS[:-1]], ignore_index=True)),
        "note": "Reference winner and probabilities are unchanged. The candidate only reorders a target day's "
                "known archive fixtures within each league. Point-in-time calendar completeness is unverified.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        report = evaluate()
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
