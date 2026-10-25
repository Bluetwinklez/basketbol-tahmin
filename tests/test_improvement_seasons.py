import importlib.util
from pathlib import Path

import pandas as pd


def test_target_seasons_use_explicit_pinned_clock():
    spec=importlib.util.spec_from_file_location('basketball_ablation',Path(__file__).parents[1]/'scripts/evaluate_improvement_basketball.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    games=pd.DataFrame(dict(sezon=['2023-24','2024-25','2025-26','2026-27']))
    assert module.target_seasons(games,'2026-10-25')==['2024-25','2025-26']
    assert module.target_seasons(games,'2027-07-01')==['2025-26','2026-27']
    # Passing the pinned date always retains the original cohort, regardless
    # of the execution host's current date.
    assert module.target_seasons(games,'2026-10-25')==['2024-25','2025-26']
