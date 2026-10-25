import hashlib

from bbtahmin.artifacts import matches_text_hash


def test_checkout_line_endings_do_not_invalidate_text_evidence(tmp_path):
    path=tmp_path/'metrics.csv';lf=b'league,accuracy\nE,0.6\n';windows=lf.replace(b'\n',b'\r\n')
    path.write_bytes(windows)
    assert matches_text_hash(path,hashlib.sha256(lf).hexdigest())
    path.write_bytes(lf)
    assert matches_text_hash(path,hashlib.sha256(windows).hexdigest())
    path.write_bytes(lf.replace(b'0.6',b'0.9'))
    assert not matches_text_hash(path,hashlib.sha256(lf).hexdigest())
