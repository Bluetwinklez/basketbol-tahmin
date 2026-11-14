import pytest
from bbtahmin.football.turkey_second import import_2019
from bbtahmin.football.data import parse_text


def source():
    games='\n'.join(f'  T{h}  v  T{a}    1-0' for h in range(18) for a in range(18) if h!=a)
    return '= Turkish 1. Lig 2019/20\nSun Jul 19\n'+games+'\n▪ Playoffs, Semifinals\n  A  v  B    5-6 pen.\n'


def test_import_excludes_playoffs_and_keeps_july_in_2020(tmp_path):
    rows=import_2019(source(),'source','2026-11-14',tmp_path)
    assert len(rows)==306
    assert {r['date'] for r in rows}=={'2020-07-19'}
    assert {r['league'] for r in rows}=={'TR2'}
    assert all(r['source_kind']=='community_CC0_not_official' for r in rows)
    with pytest.raises(ValueError): parse_text(source(),'TR1','2019-20','source','2026-11-14')


def test_incomplete_or_conflicting_import_retains_archive(tmp_path):
    import_2019(source(),'source','2026-11-14',tmp_path)
    target=tmp_path/'TR2_2019-20.json.gz'; before=target.read_bytes()
    for text in (source().replace('  T0  v  T1    1-0\n',''),
                 source().replace('▪ Playoffs, Semifinals','Other stage'),
                 source().replace('1-0','2-0')):
        with pytest.raises(ValueError): import_2019(text,'source','2026-11-14',tmp_path)
        assert target.read_bytes()==before
