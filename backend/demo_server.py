"""Loopback-only demo API and static UI, using actual model implementations."""
import argparse
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from backend.demo_engine import DemoEngine, SCENARIOS
from backend.test_lab import sample_wav, run_test


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, engine, static_root):
        self.engine, self.static_root = engine, str(static_root)
        self.state_lock = threading.RLock()
        super().__init__(address, DemoHandler)


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=args[2].static_root, **kwargs)

    def end_headers(self):
        if not urlsplit(self.path).path.startswith('/api/'):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def send_head(self):
        # Local demo edits must not retain a platform/browser-cached HTML page.
        if 'If-Modified-Since' in self.headers:
            del self.headers['If-Modified-Since']
        return super().send_head()

    def _allowed(self):
        host = self.headers.get('Host', '')
        port = self.server.server_address[1]
        return host in (f'127.0.0.1:{port}', f'localhost:{port}')

    def _json(self, value, status=200):
        encoded = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if not self._allowed():
            return self._json({'error': 'Local host required'}, 403)
        path = urlsplit(self.path).path
        if path.startswith('/api/lab/audio/'):
            try:
                audio = sample_wav(path.rsplit('/', 1)[-1], parse_qs(urlsplit(self.path).query).get('crew_id',['AST-01'])[0])
            except ValueError as error:
                return self._json({'error': str(error)}, 400)
            self.send_response(200)
            self.send_header('Content-Type', 'audio/wav')
            self.send_header('Content-Length', str(len(audio)))
            self.end_headers()
            self.wfile.write(audio)
            return
        if path == '/api/progress':
            from copy import deepcopy
            return self._json(deepcopy(self.server.engine.progress) or {'status':'idle'})
        if path == '/api/health':
            return self._json({'status': 'ready', 'scenarios': SCENARIOS, 'data_origin': 'synthetic'})
        if path == '/api/mission':
            with self.server.state_lock:
                return self._json(self.server.engine.bundle())
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/astral-prototype/')
            self.end_headers()
            return
        if path.startswith('/api/'):
            return self._json({'error': 'Unknown endpoint'}, 404)
        return super().do_GET()

    def do_POST(self):
        if not self._allowed():
            return self._json({'error': 'Local host required'}, 403)
        origin = self.headers.get('Origin')
        if origin is not None and origin not in (f'http://127.0.0.1:{self.server.server_address[1]}', f'http://localhost:{self.server.server_address[1]}'):
            return self._json({'error': 'Same-origin demo requests required'}, 403)
        path = urlsplit(self.path).path
        if path not in ('/api/demo/run', '/api/reviews', '/api/lab/test', '/api/crew/checkin', '/api/mission/analyze', '/api/crew/draft'):
            return self._json({'error': 'Unknown endpoint'}, 404)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= (6 * 1024 * 1024 if path == '/api/lab/test' else 8192):
                raise ValueError('Expected a small JSON request')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('JSON object required')
        except (ValueError, TypeError) as error:
            return self._json({'error': str(error)}, 400)
        if not self.server.state_lock.acquire(blocking=False):
            return self._json({'error': 'A demo is running. Try again shortly.'}, 409)
        try:
            if path == '/api/crew/draft':
                return self._json(self.server.engine.entries.draft(data.get('crew_id'),data.get('voice'),data.get('wearable'),data.get('scenario','baseline')))
            if path in ('/api/crew/checkin','/api/mission/analyze'):
                from copy import deepcopy
                selected = deepcopy(self.server.engine.checkins)
                if path == '/api/crew/checkin':
                    draft = None
                    if data.get('draft_id'):
                        draft = self.server.engine.entries.get_draft(data['draft_id'], data.get('crew_id'))
                        data = {**data, **{key:draft[key] for key in ('voice','wearable','scenario')}}
                    selected[data.get('crew_id')] = {'voice':data.get('voice'), 'wearable':data.get('wearable')}
                    if draft:
                        selected[data['crew_id']]['draft_readings'] = draft['member']['biometrics']
                self.server.engine.run(data.get('scenario','baseline'), checkins=selected, operation_id=data.get('operation_id'))
                if path == '/api/crew/checkin':
                    from datetime import datetime, timezone
                    current = self.server.engine.bundle()['overview']
                    member = next(m for m in current['snapshot']['payload']['crew'] if m['crew_id']==data['crew_id'])
                    self.server.engine.entries.save(data['crew_id'],datetime.now(timezone.utc).isoformat(),{
                        'kind':'submitted','data_origin':'synthetic','member':member,'voice':data['voice'],'wearable':data['wearable'],
                        'snapshot_id':current['snapshot']['id'],'analysis_id':current['current_analysis']['id']})
                    if draft:self.server.engine.entries.drafts.pop(draft['draft_id'],None)
                return self._json(self.server.engine.bundle())
            if path == '/api/lab/test':
                return self._json(run_test(self.server.engine, data))
            if path == '/api/demo/run':
                self.server.engine.run(data.get('scenario'), operation_id=data.get('operation_id'))
            else:
                view = self.server.engine.service.overview()
                current = view['current_analysis']
                if (current is None or current['id'] != data.get('analysis_id')
                        or view['snapshot']['id'] != data.get('snapshot_id')
                        or view['snapshot']['payload'].get('run_id') != data.get('run_id')):
                    raise ValueError('Review must refer to the current fresh analysis')
                reviewer, note = data.get('reviewer'), data.get('note')
                if not isinstance(reviewer, str) or len(reviewer) > 80 or not isinstance(note, str) or len(note) > 1000:
                    raise ValueError('Reviewer/note length is invalid')
                self.server.engine.service.record_review(current['id'], reviewer=reviewer,
                                                         decision=data.get('decision'), note=note)
            return self._json(self.server.engine.bundle())
        except (ValueError, TypeError) as error:
            if path in ('/api/crew/checkin','/api/mission/analyze','/api/demo/run') and self.server.engine.progress:
                self.server.engine.progress = {**self.server.engine.progress, 'status':'failed'}
            return self._json({'error': str(error)}, 400)
        finally:
            self.server.state_lock.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--database', type=Path, default=Path('runtime/demo.sqlite3'))
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.database.parent.mkdir(parents=True, exist_ok=True)
    print('Loading voice baselines and wearable model...', flush=True)
    engine = DemoEngine(args.database, root / 'models/wearable/model.json')
    if engine.service.store.latest() is None:
        engine.run('baseline')
    server = DemoServer(('127.0.0.1', args.port), engine, root / 'ui')
    print(f'Local synthetic demo ready: http://127.0.0.1:{args.port}/astral-prototype/', flush=True)
    if args.open_browser:
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{args.port}/astral-prototype/')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
