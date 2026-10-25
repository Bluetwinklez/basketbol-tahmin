"""The target labels must never select calibration or candidate policy."""
import copy

import pytest


def test_target_results_do_not_change_prior_selection(monkeypatch):
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('improvement_football',Path(__file__).parents[1]/'scripts/evaluate_improvement_football.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    def make(season,flip=False):
        rows=[]
        for i in range(80):
            for variant in module.VARIANTS:
                rows.append(dict(event_id=f'{season}-{i}',day=f'{season[:4]}-{1+i//28:02d}-{1+i%28:02d}',
                                 league='EN1',season=season,variant=variant,y=(i%3 if not flip else (i+1)%3),
                                 p=[.45,.3,.25],data_gate_passed=True,
                                 result={k:1. for k in ('home_absolute_error','away_absolute_error','total_absolute_error','margin_absolute_error','total_in_80')}))
        return rows,[]
    monkeypatch.setattr(module,'season_predictions',lambda f,l,s:make(s))
    before=module.compare(None,'EN1','2025-26','2024-25',bootstrap=20)
    monkeypatch.setattr(module,'season_predictions',lambda f,l,s:make(s,flip=s=='2025-26'))
    after=module.compare(None,'EN1','2025-26','2024-25',bootstrap=20)
    assert before['temperatures']==after['temperatures']
    assert before['selected_using_prior_period']==after['selected_using_prior_period']
    assert before['selection_metrics']==after['selection_metrics']
    assert before['production_default_changed'] is False
    with pytest.raises(ValueError): module.compare(None,'EN1','2024-25','2025-26')
