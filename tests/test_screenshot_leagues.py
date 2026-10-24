import gzip,json
import pytest
from bbtahmin.football.data import row,parse_text
from bbtahmin.football.screenshots import save

def test_conflicting_scores_leave_original(tmp_path):
    a=row('AR2','2026','2026-10-01','A','B',[1,0],'source','2026-10-25')
    save([a],'AR2','2026',tmp_path);p=tmp_path/'AR2_2026.json.gz';original=p.read_bytes()
    with pytest.raises(ValueError):save([dict(a,home_goals=3)],'AR2','2026',tmp_path)
    assert p.read_bytes()==original
    with pytest.raises(ValueError):save([a,a],'AR2','2025',tmp_path)

def test_mexico_competition_is_explicit():
    text='= Liga de Expansión MX 2024/25\nSat Aug 3 2024\n  A  v  B    2-1\n'
    assert parse_text(text,'MX2','2024-25','source','2026-10-25')[0]['league']=='MX2'
    with pytest.raises(ValueError):parse_text(text,'TR1','2024-25','source','2026-10-25')
