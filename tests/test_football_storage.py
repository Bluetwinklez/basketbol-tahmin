"""Empty upstream responses must not erase fixtures or claim fresh coverage."""
import pytest
from bbtahmin.football.data import row
from bbtahmin.football.storage import save


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("as_generator", [False, True])
def test_empty_snapshot_preserves_archive(tmp_path, existing, as_generator):
    target = tmp_path / "US1_2024.json.gz"
    if existing:
        rows = [
            row("US1", "2024", "2024-04-01", "A", "B", [2, 1], "source", "2025-01-01"),
            row("US1", "2024", "2024-04-02", "C", "D", None, "source", "2025-01-01"),
        ]
        save(rows, "US1", "2024", tmp_path)
    before = target.read_bytes() if existing else None
    with pytest.raises(ValueError, match="Empty football source snapshot"):
        save(iter([]) if as_generator else [], "US1", "2024", tmp_path)
    assert target.exists() == existing
    if existing:
        assert target.read_bytes() == before
    assert not list(tmp_path.glob("*.part"))


def test_failed_replace_preserves_archive_and_cleans_own_staging(tmp_path, monkeypatch):
    from pathlib import Path
    rows=[row('US1','2024','2024-04-01','A','B',[2,1],'source','2025-01-01')]
    save(rows,'US1','2024',tmp_path)
    target=tmp_path/'US1_2024.json.gz'; before=target.read_bytes()
    unrelated=tmp_path/'US1_2024.json.part'; unrelated.write_bytes(b'other writer')
    attempted=[]
    def fail(path, destination):
        attempted.append(path)
        assert destination==target and path!=unrelated
        assert path.read_bytes()
        raise OSError('simulated replacement failure')
    monkeypatch.setattr(Path,'replace',fail)
    with pytest.raises(OSError,match='replacement failure'):
        save(rows,'US1','2024',tmp_path)
    assert target.read_bytes()==before
    assert unrelated.read_bytes()==b'other writer'
    assert attempted and all(not p.exists() for p in attempted)


def test_success_does_not_clobber_another_staging_file(tmp_path):
    import gzip
    import json
    unrelated=tmp_path/'US1_2024.json.part'; unrelated.write_bytes(b'other writer')
    rows=[row('US1','2024','2024-04-01','A','B',[0,0],'source','2025-01-01')]
    save(rows,'US1','2024',tmp_path)
    assert json.loads(gzip.decompress((tmp_path/'US1_2024.json.gz').read_bytes()))['rows']==rows
    assert unrelated.read_bytes()==b'other writer'
    assert sorted(tmp_path.glob('*.part'))==[unrelated]
