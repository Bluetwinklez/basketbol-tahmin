from pathlib import Path
import runpy

import pandas as pd
import pytest


def test_confidence_report_cannot_hide_coverage_or_small_sample_uncertainty():
    function=runpy.run_path(str(Path(__file__).parents[1]/'scripts/confidence_report.py'))['confidence_table']
    data=pd.DataFrame(dict(lig=['NBA']*3,model=['skor']*3,p=[.9,.7,.55],y=[1,0,1]))
    result=function(data,thresholds=[.5,.8,.95]).set_index('threshold')
    assert result.loc[.5,'accuracy']==pytest.approx(2/3)
    assert result.loc[.8,'coverage']==pytest.approx(1/3)
    assert result.loc[.8,'selected_games']==1
    assert result.loc[.8,'wilson95_low']<.3
    assert result.loc[.95,'selected_games']==0 and pd.isna(result.loc[.95,'accuracy'])
