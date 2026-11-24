import base64
import gzip
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from bbtahmin.prospective import PREDICTION_MODULES, canonical, fingerprint, prediction_fingerprint
from bbtahmin.shadow import evaluate, register, save_new


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path('src/bbtahmin')

NON_PREDICTION = {
    '__init__.py': 'Package marker.',
    '__main__.py': 'CLI dispatch.',
    'app.py': 'Web server and UI endpoints.',
    'backtest.py': 'Historical training/evaluation runner and artifact writer.',
    'bulletin.py': 'Market event listing and forecast adapter.',
    'context_import.py': 'Observation archive ingestion.',
    'daily.py': 'Daily orchestration and fixture/result transport.',
    'defter.py': 'Prediction ledger and settlement output.',
    'eda.py': 'Exploratory data summaries.',
    'euro_facts.py': 'Publisher fixture and result ingestion.',
    'experiment_status.py': 'Reports on saved experiment records.',
    'football/__init__.py': 'Package marker.',
    'football/calendar.py': 'Calendar ingestion.',
    'football/coverage.py': 'Archive coverage and history summaries.',
    'football/daily.py': 'Separate native football forecast and settlement ledger.',
    'football/evaluation_audit.py': 'Post-hoc football comparison audit.',
    'football/exports.py': 'CSV and Markdown formatting.',
    'football/fixture_confirmation.py': 'Produces the independent fixture snapshot.',
    'football/regional.py': 'Regional football ingestion.',
    'football/screenshots.py': 'Football snapshot import.',
    'football/storage.py': 'Collector-side archive validation and writes.',
    'football/turkey_second.py': 'Historical football archive import.',
    'four_factors.py': 'Historical feature ablation outside the pregame forecast paths.',
    'live.py': 'Separate in-game prediction models.',
    'live_feed.py': 'Live observation ingestion.',
    'live_scorecard.py': 'Post-hoc performance reporting.',
    'market_estimates.py': 'Display estimates derived from a finished forecast.',
    'market_history.py': 'Reads and presents archived odds observations.',
    'mcp_server.py': 'MCP tool wrappers.',
    'monitoring.py': 'Diagnostics for distribution shift and reliability.',
    'player_context.py': 'Standalone player observations outside forecast paths.',
    'prospective.py': 'Native frozen-record integrity and ledger functions.',
    'refresh_health.py': 'Collector health reporting and retry scheduling.',
    'report.py': 'Historical report generation.',
    'shadow.py': 'Paired forecast ledger, integrity and settlement reporting.',
    'travel.py': 'Standalone travel observations outside forecast paths.',
    'veri/__init__.py': 'Package marker.',
    'veri/aba.py': 'ABA ingestion.',
    'veri/argentina.py': 'Argentina ingestion.',
    'veri/cba.py': 'CBA ingestion.',
    'veri/cba_quarters.py': 'CBA in-game archive ingestion.',
    'veri/collect.py': 'Collector orchestration.',
    'veri/competitions.py': 'Competition ingestion and archive writes.',
    'veri/domestic.py': 'Domestic competition ingestion.',
    'veri/euroleague.py': 'EuroLeague ingestion and overlay source parser.',
    'veri/finland.py': 'Finland ingestion.',
    'veri/genislet.py': 'Historical archive expansion.',
    'veri/http.py': 'Collector HTTP transport and cache.',
    'veri/iddaa.py': 'Market bulletin ingestion and archive reads.',
    'veri/japan.py': 'Japan ingestion.',
    'veri/korea.py': 'Korea ingestion.',
    'veri/kutu.py': 'Box score ingestion.',
    'veri/nba_bref.py': 'Basketball Reference ingestion.',
    'veri/nba_kutu.py': 'NBA box score ingestion.',
    'veri/nba_odds.py': 'NBA odds ingestion.',
    'veri/nba_oyuncu.py': 'NBA player archive ingestion.',
    'veri/nba_schedule.py': 'NBA schedule ingestion.',
    'veri/pba_current.py': 'Current PBA ingestion.',
    'veri/philippines.py': 'Philippines ingestion.',
    'veri/public_bytes.py': 'Collector transport.',
    'veri/regional.py': 'Regional source ingestion helpers.',
    'veri/sakatlik.py': 'Optional NBA injury report ingestion.',
    'veri/schema.py': 'Collector-side archive normalization.',
    'veri/slovenia.py': 'Slovenia ingestion.',
    'veri/spain.py': 'Spain ingestion.',
    'veri/turkey.py': 'Turkey ingestion.',
    'veri/ukraine.py': 'Ukraine ingestion.',
    'veri/waba.py': 'WABA ingestion.',
    'veri/women_history.py': 'Historical women’s competition ingestion.',
}


@pytest.fixture
def source_tree(tmp_path_factory):
    root = tmp_path_factory.mktemp('scope')
    shutil.copytree(ROOT / 'src', root / 'src', ignore=shutil.ignore_patterns('__pycache__'))
    return root


def test_every_python_module_is_classified():
    package = ROOT / PACKAGE
    actual = {path.relative_to(package).as_posix() for path in package.rglob('*.py')}
    included = set(PREDICTION_MODULES)
    excluded = set(NON_PREDICTION)
    assert len(included) == len(PREDICTION_MODULES), 'Duplicate prediction module'
    assert not included & excluded, f'Conflicting classifications: {sorted(included & excluded)}'
    assert not actual - included - excluded, f'Unclassified modules: {sorted(actual - included - excluded)}'
    assert not (included | excluded) - actual, f'Stale classifications: {sorted((included | excluded) - actual)}'


@pytest.mark.parametrize('module,changes', [('app.py', False), ('football/health.py', True)])
def test_prediction_fingerprint_scope(source_tree, module, changes):
    before = prediction_fingerprint(source_tree)
    full_before = fingerprint(source_tree)
    target = source_tree / PACKAGE / module
    target.write_bytes(target.read_bytes() + b'\n# source edit\n')
    assert (prediction_fingerprint(source_tree) != before) == changes
    assert fingerprint(source_tree) != full_before


def test_prediction_fingerprint_uses_sorted_paths_and_raw_bytes(source_tree):
    paths = sorted(f'{PACKAGE.as_posix()}/{module}' for module in PREDICTION_MODULES)
    data = b''.join(path.encode() + b'\0' + (source_tree / path).read_bytes() for path in paths)
    assert prediction_fingerprint(source_tree) == hashlib.sha256(data).hexdigest()
    (source_tree / paths[0]).unlink()
    with pytest.raises(FileNotFoundError):
        prediction_fingerprint(source_tree)


def test_register_reuses_cohort_only_for_excluded_edits(source_tree):
    output = source_tree / 'out'
    policy = {'version': 1}
    original, identity = register(output, policy, source_root=source_tree)
    protocol_path = original / 'protocol.json'
    snapshot_path = original / 'source_snapshot.json.gz'
    original_protocol = protocol_path.read_bytes()
    original_snapshot = snapshot_path.read_bytes()
    protocol = json.loads(original_protocol)
    assert protocol['spec'] == 'paired-forward-policy-v4'
    assert protocol['prediction_code_sha256'] == prediction_fingerprint(source_tree)
    assert 'source_code_sha256' not in protocol

    excluded = source_tree / PACKAGE / 'live_scorecard.py'
    excluded.write_bytes(excluded.read_bytes() + b'\n# scorecard edit\n')
    assert register(output, policy, source_root=source_tree) == (original, identity)

    included = source_tree / PACKAGE / 'model.py'
    included.write_bytes(included.read_bytes() + b'\n# model edit\n')
    changed, changed_id = register(output, policy, source_root=source_tree)
    assert changed != original and changed_id != identity
    assert protocol_path.read_bytes() == original_protocol
    assert snapshot_path.read_bytes() == original_snapshot
    assert evaluate(original, [])['source_snapshot_verified']
    assert evaluate(changed, [])['source_snapshot_verified']

    snapshot = json.loads(gzip.decompress(original_snapshot))
    assert set(snapshot['files']) == {f'{PACKAGE.as_posix()}/{module}' for module in PREDICTION_MODULES}
    snapshot['files'][f'{PACKAGE.as_posix()}/model.py'] = base64.b64encode(b'tampered').decode('ascii')
    snapshot_path.write_bytes(gzip.compress(canonical(snapshot)))
    with pytest.raises(ValueError, match='Frozen source snapshot fingerprint mismatch'):
        evaluate(original, [])


def test_legacy_full_source_snapshot_still_verifies(source_tree):
    saved = source_tree / 'legacy'
    save_new(saved / 'protocol.json', {
        'spec': 'paired-forward-policy-v3', 'source_code_sha256': fingerprint(source_tree),
    })
    files = {path.relative_to(source_tree).as_posix(): base64.b64encode(path.read_bytes()).decode('ascii')
             for path in (source_tree / 'src').rglob('*.py')}
    (saved / 'source_snapshot.json.gz').write_bytes(gzip.compress(canonical({'files': files})))
    assert evaluate(saved, [])['source_snapshot_verified']
