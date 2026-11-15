"""Local or explicitly configured public demo API and static UI."""
import argparse
import base64
import hashlib
from http.cookies import SimpleCookie
import json
import os
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from backend.demo_engine import DemoEngine, SCENARIOS
from backend.public_sessions import PublicSessions, SessionCapacityError, SESSION_SECONDS
from backend.test_lab import sample_wav, run_test

COOKIE_NAME = '__Host-astral_demo'
POST_ENDPOINTS = ('/api/demo/run', '/api/reviews', '/api/lab/test', '/api/crew/checkin',
                  '/api/mission/analyze', '/api/crew/draft')


def configured_public_origin(value):
    """Fail closed if the trusted HTTPS URL is not an exact web origin."""
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment or parsed.port is not None):
        raise ValueError('Public demo requires a plain HTTPS origin, e.g. https://astral.onrender.com')
    return f'https://{parsed.hostname.lower()}'


def csp_for(static_root):
    html = (Path(static_root) / 'astral-prototype/index.html').read_text(encoding='utf-8')
    scripts = re.findall(r'<script(?![^>]*type="application/json")(?![^>]*src=)[^>]*>(.*?)</script>',
                         html, flags=re.S)
    hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"
              for script in scripts if script.strip()]
    return ("default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; "
            "form-action 'self'; script-src 'self' " + ' '.join(hashes) + "; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
            "media-src 'self' blob:; connect-src 'self'; upgrade-insecure-requests")


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, engine, static_root, *, public_origin=None):
        self.engine, self.static_root = engine, str(static_root)
        self.public_origin = configured_public_origin(public_origin) if public_origin else None
        self.public_host = urlsplit(self.public_origin).netloc if self.public_origin else None
        self.sessions = (PublicSessions(Path(self.static_root).parent / 'models/wearable/model.json')
                         if self.public_origin else None)
        self.content_security_policy = csp_for(self.static_root) if self.public_origin else None
        self.state_lock = threading.RLock()
        super().__init__(address, DemoHandler)

    def server_close(self):
        super().server_close()
        if self.sessions:
            self.sessions.close()


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=args[2].static_root, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if self.server.public_origin:
            self.send_header('Strict-Transport-Security', 'max-age=31536000')
            self.send_header('Content-Security-Policy', self.server.content_security_policy)
        super().end_headers()

    def send_head(self):
        # Local demo edits must not retain a platform/browser-cached HTML page.
        if 'If-Modified-Since' in self.headers:
            del self.headers['If-Modified-Since']
        return super().send_head()

    def _allowed(self):
        host = self.headers.get('Host', '')
        if self.server.public_host:
            return host == self.server.public_host
        port = self.server.server_address[1]
        return host in (f'127.0.0.1:{port}', f'localhost:{port}')

    def _session(self):
        if not self.server.sessions:
            return None
        raw = self.headers.get('Cookie', '')
        if len(raw) > 4096:
            return None
        try:
            parsed = SimpleCookie()
            parsed.load(raw)
            token = parsed[COOKIE_NAME].value if COOKIE_NAME in parsed else None
        except Exception:
            return None
        return self.server.sessions.get(token) if token else None

    def _json(self, value, status=200, cookie=None):
        encoded = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        if cookie:
            self.send_header('Set-Cookie', f'{COOKIE_NAME}={cookie}; Path=/; Max-Age={SESSION_SECONDS}; Secure; HttpOnly; SameSite=Strict')
        self.end_headers()
        self.wfile.write(encoded)

    def _set_static_root(self, path):
        if path.startswith('/submission-assets/'):
            self.directory = str(Path(self.server.static_root).parent / 'submission' / 'astral-prototype')
            self.path = path[len('/submission-assets'):]
        elif path.startswith('/data/'):
            self.directory = str(Path(self.server.static_root).parent / 'submission' / 'data')
            self.path = path[len('/data'):]

    def do_HEAD(self):
        if not self._allowed():
            self.send_error(403, 'Unrecognized host')
            return
        path = urlsplit(self.path).path
        if path.startswith('/api/'):
            self.send_error(405, 'GET or POST required')
            return
        self._set_static_root(path)
        return super().do_HEAD()

    def do_GET(self):
        if not self._allowed():
            return self._json({'error': 'Unrecognized host'}, 403)
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
            session = self._session()
            if self.server.sessions and session is None:
                return self._json({'error': 'Session expired; refresh the page to restart.'}, 401)
            engine = session.engine if session else self.server.engine
            return self._json(deepcopy(engine.progress) or {'status':'idle'})
        if path == '/api/health':
            return self._json({'status': 'ready', 'scenarios': SCENARIOS, 'data_origin': 'synthetic',
                               'public_demo': bool(self.server.sessions),
                               'uploads_enabled': not bool(self.server.sessions)})
        if path == '/api/mission':
            session = self._session()
            if self.server.sessions and session is None:
                return self._json({'error': 'Session expired; refresh the page to restart.'}, 401)
            engine = session.engine if session else self.server.engine
            with self.server.state_lock:
                data = engine.bundle()
                data['demo_server']['public_demo'] = bool(self.server.sessions)
                return self._json(data)
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/astral-prototype/')
            self.end_headers()
            return
        if path.startswith('/api/'):
            return self._json({'error': 'Unknown endpoint'}, 404)
        self._set_static_root(path)
        return super().do_GET()

    def do_POST(self):
        if not self._allowed():
            return self._json({'error': 'Unrecognized host'}, 403)
        origin = self.headers.get('Origin')
        local_origins = (f'http://127.0.0.1:{self.server.server_address[1]}',
                         f'http://localhost:{self.server.server_address[1]}')
        if (self.server.sessions and origin != self.server.public_origin) or (not self.server.sessions and origin is not None and origin not in local_origins):
            return self._json({'error': 'Same-origin demo requests required'}, 403)
        path = urlsplit(self.path).path
        if path != '/api/session' and path not in POST_ENDPOINTS:
            return self._json({'error': 'Unknown endpoint'}, 404)
        if path == '/api/session' and not self.server.sessions:
            return self._json({'error': 'Public sessions are not enabled'}, 404)
        session = self._session()
        if self.server.sessions and path != '/api/session' and session is None:
            return self._json({'error': 'Session expired; refresh the page to restart.'}, 401)
        if self.server.sessions and path == '/api/session' and session:
            return self._json({'status': 'ready', 'public_demo': True})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            max_size = 8192 if self.server.sessions else (6 * 1024 * 1024 if path == '/api/lab/test' else 8192)
            if not 0 < length <= max_size:
                raise ValueError('Expected a small JSON request')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('JSON object required')
        except (ValueError, TypeError) as error:
            return self._json({'error': str(error)}, 400)
        if path == '/api/session':
            try:
                session = self.server.sessions.create()
            except SessionCapacityError:
                return self._json({'error': 'Public demo temporarily at capacity; try again later.'}, 503)
            return self._json({'status': 'ready', 'public_demo': True}, cookie=session.token)
        if self.server.sessions and path == '/api/lab/test' and (data.get('sample') == 'upload' or any(k in data for k in ('signals', 'baseline_wavs', 'test_wav'))):
            return self._json({'error': 'Personal file uploads are disabled on the public demo. Use the generated samples.'}, 403)
        if self.server.sessions and not session.allow_write():
            return self._json({'error': 'Demo request limit reached. Please wait one minute.'}, 429)
        if not self.server.state_lock.acquire(blocking=False):
            return self._json({'error': 'A demo is running. Try again shortly.'}, 409)
        engine = session.engine if session else self.server.engine
        try:
            if path == '/api/crew/draft':
                return self._json(engine.entries.draft(data.get('crew_id'),data.get('voice'),data.get('wearable'),data.get('scenario','baseline')))
            if path in ('/api/crew/checkin','/api/mission/analyze'):
                from copy import deepcopy
                selected = deepcopy(engine.checkins)
                if path == '/api/crew/checkin':
                    draft = None
                    if data.get('draft_id'):
                        draft = engine.entries.get_draft(data['draft_id'], data.get('crew_id'))
                        data = {**data, **{key:draft[key] for key in ('voice','wearable','scenario')}}
                    selected[data.get('crew_id')] = {'voice':data.get('voice'), 'wearable':data.get('wearable')}
                    if draft:
                        selected[data['crew_id']]['draft_readings'] = draft['member']['biometrics']
                engine.run(data.get('scenario','baseline'), checkins=selected, operation_id=data.get('operation_id'))
                if path == '/api/crew/checkin':
                    from datetime import datetime, timezone
                    current = engine.bundle()['overview']
                    member = next(m for m in current['snapshot']['payload']['crew'] if m['crew_id']==data['crew_id'])
                    engine.entries.save(data['crew_id'],datetime.now(timezone.utc).isoformat(),{
                        'kind':'submitted','data_origin':'synthetic','member':member,'voice':data['voice'],'wearable':data['wearable'],
                        'snapshot_id':current['snapshot']['id'],'analysis_id':current['current_analysis']['id']})
                    if draft:engine.entries.drafts.pop(draft['draft_id'],None)
                result = engine.bundle()
                result['demo_server']['public_demo'] = bool(self.server.sessions)
                return self._json(result)
            if path == '/api/lab/test':
                return self._json(run_test(engine, data))
            if path == '/api/demo/run':
                engine.run(data.get('scenario'), operation_id=data.get('operation_id'))
            else:
                view = engine.service.overview()
                current = view['current_analysis']
                if (current is None or current['id'] != data.get('analysis_id')
                        or view['snapshot']['id'] != data.get('snapshot_id')
                        or view['snapshot']['payload'].get('run_id') != data.get('run_id')):
                    raise ValueError('Review must refer to the current fresh analysis')
                reviewer, note = data.get('reviewer'), data.get('note')
                if not isinstance(reviewer, str) or len(reviewer) > 80 or not isinstance(note, str) or len(note) > 1000:
                    raise ValueError('Reviewer/note length is invalid')
                engine.service.record_review(current['id'], reviewer=reviewer,
                                                         decision=data.get('decision'), note=note)
            result = engine.bundle()
            result['demo_server']['public_demo'] = bool(self.server.sessions)
            return self._json(result)
        except (ValueError, TypeError) as error:
            if path in ('/api/crew/checkin','/api/mission/analyze','/api/demo/run') and engine.progress:
                engine.progress = {**engine.progress, 'status':'failed'}
            return self._json({'error': str(error)}, 400)
        finally:
            self.server.state_lock.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=None)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--public', action='store_true', help='Public HTTPS demo with isolated temporary sessions')
    parser.add_argument('--database', type=Path, default=Path('runtime/demo.sqlite3'))
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args()
    args.port = args.port if args.port is not None else int(os.environ.get('PORT', '10000' if args.public else '8765'))
    root = Path(__file__).resolve().parents[1]
    if not args.public and args.host not in ('127.0.0.1', 'localhost'):
        parser.error('A non-loopback bind requires --public and an HTTPS public origin')
    public_origin = None
    if args.public:
        try:
            public_origin = configured_public_origin(os.environ.get('ASTRAL_PUBLIC_ORIGIN') or os.environ.get('RENDER_EXTERNAL_URL', ''))
        except ValueError as error:
            parser.error(str(error))
        engine = None
    else:
        args.database.parent.mkdir(parents=True, exist_ok=True)
        print('Loading voice baselines and wearable model...', flush=True)
        engine = DemoEngine(args.database, root / 'models/wearable/model.json')
        if engine.service.store.latest() is None:
            engine.run('baseline')
    server = DemoServer((args.host, args.port), engine, root / 'ui', public_origin=public_origin)
    print(f'Synthetic demo ready: {public_origin or f"http://127.0.0.1:{args.port}"}/astral-prototype/', flush=True)
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
