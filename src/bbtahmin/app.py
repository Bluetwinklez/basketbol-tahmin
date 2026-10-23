"""Local browser application for the existing daily research workflow.

Loopback only, no extra web framework, one background model job at a time.
The browser cannot choose filesystem paths or execute arbitrary commands.
"""
import copy
import csv
import io
import json
import math
import secrets
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from .daily import LEAGUES, markdown, run


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def options(payload):
    if not isinstance(payload, dict) or set(payload) - {'leagues', 'hours', 'threshold', 'refresh'}:
        raise ValueError('Unknown run options')
    leagues = payload.get('leagues', list(LEAGUES))
    hours, threshold, refresh = payload.get('hours', 48), payload.get('threshold', .65), payload.get('refresh', False)
    if (not isinstance(leagues, list) or not 1 <= len(leagues) <= len(LEAGUES) or
            any(not isinstance(c, str) or c not in LEAGUES for c in leagues)):
        raise ValueError('Choose at least one supported league')
    if type(hours) is not int or not 1 <= hours <= 168:
        raise ValueError('Fixture horizon must be 1..168 hours')
    if (type(threshold) not in (int, float) or not math.isfinite(threshold) or not .5 <= threshold <= 1):
        raise ValueError('Probability filter must be between 50% and 100%')
    if type(refresh) is not bool:
        raise ValueError('Refresh must be true or false')
    return dict(leagues=list(dict.fromkeys(leagues)), hours=hours, threshold=threshold, update=refresh)


def load_report(directory):
    """Use the local ledger; label the checked-in verification run as a sample."""
    for folder, sample in ((Path(directory), False), (Path('docs/kanit/daily_runtime'), True)):
        for path in sorted(folder.glob('check_*.json'), reverse=True):
            try:
                report = json.loads(path.read_text('utf8'))
                if report.get('spec') == 'daily-research-v1':
                    return report, sample
            except (OSError, ValueError, AttributeError):
                continue
    return None, False


def result_rows(report):
    """Attach the frozen forecast to settlements; never synthesize a prediction."""
    rows = []
    for check in (report or {}).get('settlements', []):
        record = Path(check['record'])
        predictions = {}
        try:
            from .prospective import verify
            payload = verify(json.loads(record.read_text('utf8')))
            predictions = {item['fixture']['event_id']: item for item in payload['forecasts']}
        except (OSError, ValueError, KeyError, TypeError):
            pass
        for game in check['games']:
            item = predictions.get(game['event_id'], {})
            rows.append(dict(game=game, fixture=item.get('fixture'), prediction=item.get('prediction')))
    return rows


def export_csv(report, rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['league', 'event_id', 'home', 'away', 'status', 'forecast_home', 'forecast_away',
                     'actual_home', 'actual_away', 'winner_correct', 'home_absolute_error', 'away_absolute_error',
                     'total_absolute_error', 'margin_absolute_error', 'total_in_80', 'margin_in_80'])
    for row in rows:
        g, f, p = row['game'], row['fixture'] or {}, row['prediction'] or {}
        # Prevent spreadsheet formula execution from provider-owned names/IDs.
        def cell(value):
            if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                return "'" + value
            return value
        writer.writerow([cell(f.get('league')), cell(g['event_id']), cell(f.get('home_name', g['home'])),
                         cell(f.get('away_name', g['away'])), g['status'], p.get('ev_skor'), p.get('dep_skor'),
                         *[g.get(k) for k in ('actual_home', 'actual_away', 'winner_correct', 'home_absolute_error',
                            'away_absolute_error', 'total_absolute_error', 'margin_absolute_error', 'total_in_80', 'margin_in_80')]])
    return stream.getvalue().encode('utf-8-sig')


class AppState:
    def __init__(self, directory='rapor/daily', runner=run):
        self.directory, self.runner = str(directory), runner
        self.football_directory = str(Path(directory).parent/'football')
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='basketball-research')
        self.report, self.sample = load_report(directory)
        self.job = dict(status='idle', message='Ready', started_at=None, finished_at=None)

    def snapshot(self):
        with self.lock:
            report, sample, job = copy.deepcopy(self.report), self.sample, dict(self.job)
        if report:
            from .market_estimates import total_estimates
            for entry in report.get('upcoming', []):
                entry['total_estimates'] = total_estimates(entry['prediction'])
        age = None
        if report:
            try:
                age = max(0., (datetime.now(timezone.utc) - datetime.fromisoformat(report['checked_at_utc'])).total_seconds()/60)
            except (ValueError, TypeError):
                pass
        return dict(report=report, results=result_rows(report), sample=sample, report_age_minutes=age,
                    now_utc=utc_now(), job=job, leagues=list(LEAGUES))

    def submit(self, payload):
        config = options(payload)
        with self.lock:
            if self.job['status'] == 'running':
                raise RuntimeError('A run is already in progress')
            self.job = dict(status='running', message='Refreshing sources and checking fixtures' if config['update']
                            else 'Loading local fixtures and checking forecasts', started_at=utc_now(), finished_at=None)
        self.pool.submit(self._work, config)

    def _work(self, config):
        try:
            report = self.runner(output=self.directory, **config)
            partial = bool(report['skipped'] or any(s['status'] == 'failed' for s in report['sources'].values()))
            with self.lock:
                self.report, self.sample = report, False
                self.job.update(status='partial' if partial else 'succeeded',
                                message='Completed with unresolved inputs' if partial else 'Forecast and result check complete',
                                finished_at=utc_now())
        except Exception as exc:
            with self.lock:
                self.job.update(status='failed', message=f'{type(exc).__name__}: {exc}', finished_at=utc_now())

    def submit_football(self, payload):
        if not isinstance(payload, dict) or set(payload)-{'refresh','days'}:
            raise ValueError('Unknown football options')
        refresh,days=payload.get('refresh',False),payload.get('days',7)
        if type(refresh) is not bool or type(days) is not int or not 1<=days<=14:
            raise ValueError('Choose refresh true/false and 1..14 days')
        with self.lock:
            if self.job['status']=='running': raise RuntimeError('A run is already in progress')
            self.job=dict(status='running',message='Processing football sources',started_at=utc_now(),finished_at=None)
        self.pool.submit(self._football_work,refresh,days)

    def _football_work(self, refresh, days):
        try:
            from .football.data import collect
            from .football.daily import run as football_run
            if refresh: collect(current_only=True)
            report=football_run(days,self.football_directory)
            with self.lock:
                self.job.update(status='partial' if report['source_errors'] or report['skipped'] else 'succeeded',
                                message='Football report saved',finished_at=utc_now())
        except Exception as exc:
            with self.lock:
                self.job.update(status='failed',message=f'{type(exc).__name__}: {exc}',finished_at=utc_now())

    def football_snapshot(self):
        report=None
        path=Path(self.football_directory)/'latest.json'
        sample=False
        if not path.exists():
            path=Path('data/football_ledger/latest.json');sample=True
        if path.exists(): report=json.loads(path.read_text('utf8'))
        with self.lock: job=dict(self.job)
        from .football.data import LEAGUES as FOOTBALL_LEAGUES
        return dict(report=report,job=job,sample=sample,leagues=FOOTBALL_LEAGUES)

    def close(self):
        self.pool.shutdown(wait=True)


class AppServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port=8765, directory='rapor/daily', state=None):
        self.state = state or AppState(directory)
        super().__init__(('127.0.0.1', port), Handler)

    def server_close(self):
        super().server_close()
        self.state.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def allowed(self):
        port = self.server.server_port
        hosts = (f'127.0.0.1:{port}', f'localhost:{port}')
        return self.headers.get('Host') in hosts

    def send(self, data, content_type='application/json; charset=utf-8', status=200, filename=None):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.allowed():
            return self.send(dict(error='Invalid local host'), status=403)
        path = urlsplit(self.path).path
        assets = {'/football': ('football.html', 'text/html; charset=utf-8'),
                  '/football.js': ('football.js', 'text/javascript; charset=utf-8'),
                  '/': ('index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                  '/app.css': ('app.css', 'text/css; charset=utf-8')}
        if path in assets:
            name, kind = assets[path]
            raw = files('bbtahmin').joinpath('ui', name).read_text('utf8')
            if name in ('index.html','football.html'):
                raw = raw.replace('__CSRF_TOKEN__', self.server.state.token)
            return self.send(raw.encode('utf8'), kind)
        if path == '/api/football':
            return self.send(self.server.state.football_snapshot())
        if path in ('/api/football/export.json','/api/football/export.csv','/api/football/export.md'):
            football = self.server.state.football_snapshot()
            report = football['report']
            if not report:
                return self.send(dict(error='No football report available'), status=404)
            from .football.exports import export_csv as football_csv, markdown as football_markdown
            if path.endswith('.csv'):
                return self.send(football_csv(report), 'text/csv; charset=utf-8', filename='football-results.csv')
            if path.endswith('.md'):
                return self.send(football_markdown(report), 'text/markdown; charset=utf-8', filename='football-report.md')
            return self.send(football, filename='football-report.json')
        snapshot = self.server.state.snapshot()
        if path == '/api/state':
            return self.send(snapshot)
        report = snapshot['report']
        if path in ('/api/export.json', '/api/export.csv', '/api/export.md'):
            if not report:
                return self.send(dict(error='No report available'), status=404)
            if path.endswith('.csv'):
                return self.send(export_csv(report, snapshot['results']), 'text/csv; charset=utf-8', filename='basketball-results.csv')
            if path.endswith('.md'):
                return self.send(markdown(report).encode('utf8'), 'text/markdown; charset=utf-8', filename='basketball-report.md')
            return self.send(snapshot, filename='basketball-report.json')
        return self.send(dict(error='Not found'), status=404)

    def do_POST(self):
        port = self.server.server_port
        origin = self.headers.get('Origin')
        if (not self.allowed() or origin not in (None, f'http://127.0.0.1:{port}', f'http://localhost:{port}') or
                not secrets.compare_digest(self.headers.get('X-App-Token', ''), self.server.state.token)):
            return self.send(dict(error='Invalid local request'), status=403)
        path=urlsplit(self.path).path
        if path not in ('/api/run','/api/football/run'):
            return self.send(dict(error='Not found'), status=404)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 8192 or self.headers.get_content_type() != 'application/json':
                raise ValueError('A JSON request of at most 8 KB is required')
            payload = json.loads(self.rfile.read(size))
            if path == '/api/football/run': self.server.state.submit_football(payload)
            else: self.server.state.submit(payload)
        except (ValueError, TypeError) as exc:
            return self.send(dict(error=str(exc)), status=400)
        except RuntimeError as exc:
            return self.send(dict(error=str(exc)), status=409)
        return self.send(dict(status='running'), status=202)


def serve(port=8765, directory='rapor/daily', open_browser=True):
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError('Port must be between 0 and 65535')
    server = AppServer(port, directory)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Basketball Research app: {url}\nPress Ctrl+C to stop. Existing forecast files are preserved.', flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

