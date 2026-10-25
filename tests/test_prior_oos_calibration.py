import importlib.util
from pathlib import Path


def test_basketball_calibration_does_not_learn_from_target_labels():
    spec=importlib.util.spec_from_file_location('prior_oos_calibration',Path(__file__).parents[1]/'scripts/evaluate_improvement_calibration.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=[dict(event_id=f'{year}-{i}',day=f'{year}-10-{1+i//10:02d}',season=f'{year}-{str(year+1)[-2:]}',
               variant='baseline',y=i%2,p=[.8,.2]) for year in (2024,2025) for i in range(100)]
    before=module.evaluate(rows)
    changed=[dict(r,y=1-r['y']) if r['season']=='2025-26' else r for r in rows]
    after=module.evaluate(changed)
    assert len(before)==len(after)==1
    assert before[0]['temperature']==after[0]['temperature']
    assert before[0]['last_calibration_day']<'2025-10-01'
