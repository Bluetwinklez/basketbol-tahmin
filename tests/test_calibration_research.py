import runpy
from pathlib import Path

import pandas as pd
import pytest

evaluate=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/evaluate_calibration.py'))['evaluate']


def evidence():
    return pd.DataFrame([dict(lig='NBA',sezon=season,model='skor',mac_id=f'{season}_{i}',
        p=p,y=y) for season in ['2020-21','2021-22','2022-23']
        for i,(p,y) in enumerate([(.2,0),(.4,1),(.6,0),(.8,1)])])


def test_calibration_does_not_read_target_or_future_season_outcomes():
    original=evidence();folds,p1=evaluate(original)
    altered=original.copy();altered.loc[altered.sezon>='2021-22','y']=1-altered.y
    _,p2=evaluate(altered)
    columns=['mac_id','model','p']
    pd.testing.assert_frame_equal(p1[p1.sezon=='2021-22'][columns],p2[p2.sezon=='2021-22'][columns])
    assert not (folds.calibration_last_season>=folds.sezon).any()
    assert set(p1.sezon)=={'2021-22','2022-23'}


def test_duplicate_prediction_evidence_is_rejected():
    original=evidence()
    with pytest.raises(ValueError,match='duplicate'):
        evaluate(pd.concat([original,original.iloc[:1]]))
