import pytest

from bbtahmin.prior_policy import learn


def test_forward_policy_excludes_all_current_future_outcomes():
    rows=[]
    for i in range(200):
        y=i%2
        for name,p in [('baseline',[.6,.4]),('challenger',[.8,.2] if y==0 else [.2,.8])]:
            rows.append(dict(event_id=str(i),day=f'2025-10-{1+i//10:02d}',season='2025-26',variant=name,y=y,p=p))
    expected=learn(rows,('baseline','challenger'),'2026-10-25')
    future=[dict(r,event_id='future'+r['event_id'],day='2026-11-01',season='2026-27',y=1-r['y']) for r in rows]
    assert learn(rows+future,('baseline','challenger'),'2026-10-25')==expected
    assert expected['variant']=='challenger'
    assert expected['last_prior_day']<'2026-10-25'
    with pytest.raises(ValueError):learn(rows+rows[:1],('baseline','challenger'),'2026-10-25')
