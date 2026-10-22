"""Select only complete benchmark artifacts with matching feature semantics."""
import hashlib
import json
from pathlib import Path


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
            if hashlib.sha256((root/name).read_bytes()).hexdigest()!=meta['files'][name]:
                return None
        return meta
    except (OSError,ValueError,KeyError,TypeError):
        return None


def verified_path(filename,directory='docs/kanit/pregame_verified'):
    root=Path(directory)
    return root/filename if verified_manifest(directory) and (root/filename).exists() else None


def status(directory='docs/kanit/pregame_verified'):
    manifest=verified_manifest(directory)
    if manifest is None:
        return dict(verified=False,note='Legacy parameters; refresh the pregame_verified benchmark.')
    path=Path('data/maclar.parquet')
    match=path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==manifest['dataset_sha256']
    return dict(verified=True,evaluated_at=manifest['timestamp'],dataset_matches_evaluation=bool(match),
                absence_features=bool(manifest['absence_leagues']))
