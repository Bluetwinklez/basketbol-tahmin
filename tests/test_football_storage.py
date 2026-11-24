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
