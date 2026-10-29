"""Select only complete benchmark artifacts with matching feature semantics."""
import hashlib
import json
from pathlib import Path


def matches_text_hash(path,expected):
    """Git may convert CRLF/LF on checkout; only newline variants are allowed."""
    raw=Path(path).read_bytes();lf=raw.replace(b'\r\n',b'\n')
    return expected in {hashlib.sha256(value).hexdigest() for value in (raw,lf,lf.replace(b'\n',b'\r\n'))}


def verified_manifest(directory='docs/kanit/pregame_verified'):
    from .ozellik import FEATURES
    from .eksik_ozellik import EKSIK_LIGLERI
    from .kutu_ozellik import KUTU_LIGLERI
    root=Path(directory)
    try:
        meta=json.loads((root/'manifest.json').read_text('utf8'))
        if (meta['base_features']!=FEATURES or meta['absence_leagues']!=sorted(EKSIK_LIGLERI)
                or meta['box_leagues']!=sorted(KUTU_LIGLERI)):
            return None
        for name in ('parametreler.json','metrikler.csv'):
            if name not in meta['files']:
                return None
        for name,expected in meta['files'].items():
            path=root/name
            if path.suffix=='.gz':
                valid=hashlib.sha256(path.read_bytes()).hexdigest()==expected
            else:
                valid=matches_text_hash(path,expected)
            if not valid: return None
        return meta
    except (OSError,ValueError,KeyError,TypeError):
        return None


def verified_path(filename,directory='docs/kanit/pregame_verified'):
    root=Path(directory)
    meta=verified_manifest(directory)
    return root/filename if meta and filename in meta['files'] and (root/filename).exists() else None


def require_verified_path(filename,directory='docs/kanit/pregame_verified'):
    path=verified_path(filename,directory)
    if path is None:
        raise ValueError('Missing or invalid pregame_verified benchmark; rerun '
                         'python -m bbtahmin backtest --ilk-test 2021 '
                         '--cikti docs/kanit/pregame_verified')
    return path


def status(directory='docs/kanit/pregame_verified',dataset='data/maclar.parquet'):
    manifest=verified_manifest(directory)
    if manifest is None:
        return dict(verified=False,note='Invalid benchmark; default predictions require a refresh.')
    path=Path(dataset)
    match=path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==manifest['dataset_sha256']
    return dict(verified=True,evaluated_at=manifest['timestamp'],dataset_matches_evaluation=bool(match),
                absence_features=bool(manifest['absence_leagues']))
