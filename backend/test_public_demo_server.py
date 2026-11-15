"""Public-mode security and isolation integration tests (no external network)."""
import http.client
import json
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.demo_server import DemoServer, configured_public_origin, COOKIE_NAME


ORIGIN = 'https://astral-crew.onrender.com'
ROOT = Path(__file__).resolve().parents[1]


class PublicDemoServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = DemoServer(('127.0.0.1', 0), None, ROOT / 'ui', public_origin=ORIGIN)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, path, body=None, *, cookie=None, origin=ORIGIN, host='astral-crew.onrender.com'):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=90)
        headers = {'Host': host}
        if cookie:
            headers['Cookie'] = cookie
        if body is not None:
            headers['Content-Type'] = 'application/json'
            if origin is not None:
                headers['Origin'] = origin
        try:
            connection.request('POST' if body is not None else 'GET', path,
                               body=json.dumps(body) if body is not None else None, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            data = json.loads(raw) if response.getheader('Content-Type', '').startswith('application/json') else raw
            return response.status, data, dict(response.getheaders())
        finally:
            connection.close()

    def new_session(self):
        status, data, headers = self.request('/api/session', {})
        self.assertEqual(status, 200, data)
        self.assertEqual(data['public_demo'], True)
        cookie = headers['Set-Cookie']
        self.assertTrue(cookie.startswith(COOKIE_NAME + '='))
        self.assertIn('Secure', cookie)
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Strict', cookie)
        return cookie.split(';', 1)[0]

    def test_public_site_and_health_are_available_without_a_session(self):
        status, data, headers = self.request('/api/health')
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'ready')
        self.assertTrue(data['public_demo'])
        self.assertFalse(data['uploads_enabled'])
        self.assertNotIn('Set-Cookie', headers)  # Render's health probes do not create visitors.
        self.assertIn('Strict-Transport-Security', headers)
        self.assertIn('Content-Security-Policy', headers)
        self.assertIn("script-src 'self' 'sha256-", headers['Content-Security-Policy'])
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        for path in ('/astral-prototype/', '/submission-assets/audio/manifest.json',
                     '/submission-assets/audio/ravdess/manifest.json', '/data/OSD-575_CMP_TRANSFORMED.csv'):
            status, payload, headers = self.request(path)
            self.assertEqual(status, 200, path)
            self.assertTrue(payload)
            self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')

    def test_rejects_untrusted_hosts_origins_and_missing_session(self):
        self.assertEqual(self.request('/api/health', host='attacker.invalid')[0], 403)
        self.assertEqual(self.request('/api/session', {}, origin=None)[0], 403)
        self.assertEqual(self.request('/api/session', {}, origin='https://attacker.invalid')[0], 403)
        self.assertEqual(self.request('/api/session', {}, host='attacker.invalid')[0], 403)
        self.assertEqual(self.request('/api/mission')[0], 401)
        self.assertEqual(self.request('/api/demo/run', {'scenario': 'baseline'})[0], 401)
        cookie = self.new_session()
        self.assertEqual(self.request('/api/demo/run', {'scenario': 'baseline'}, cookie=cookie, origin=None)[0], 403)
        self.assertEqual(self.request('/api/demo/run', {'scenario': 'baseline'}, cookie=cookie, origin='https://attacker.invalid')[0], 403)

    def test_isolated_sessions_and_fifth_crew(self):
        first, second = self.new_session(), self.new_session()
        tokens = [cookie.partition('=')[2] for cookie in (first, second)]
        first_engine = self.server.sessions.get(tokens[0]).engine
        second_engine = self.server.sessions.get(tokens[1]).engine
        self.assertIs(first_engine.voice, second_engine.voice)
        self.assertIsNot(first_engine.service, second_engine.service)
        _, first_before, _ = self.request('/api/mission', cookie=first)
        first_entries = first_before['member_entries']['AST-05']
        status, initial, _ = self.request('/api/mission', cookie=second)
        self.assertEqual(status, 200)
        self.assertTrue(initial['demo_server']['public_demo'])
        self.assertEqual(initial['demo_server']['crew_count'], 5)
        self.assertIn('AST-05', initial['demo_server']['supported_model_crew'])

        status, run, _ = self.request('/api/demo/run', {'scenario': 'co2_rise'}, cookie=first)
        self.assertEqual(status, 200)
        analysis, snapshot = run['overview']['current_analysis'], run['overview']['snapshot']
        status, reviewed, _ = self.request('/api/reviews', {
            'analysis_id': analysis['id'], 'snapshot_id': snapshot['id'],
            'run_id': snapshot['payload']['run_id'], 'reviewer': 'Fictional tester',
            'decision': 'follow_up', 'note': 'Private visitor note.'}, cookie=first)
        self.assertEqual(status, 200)
        self.assertEqual(reviewed['mission_logs'][0]['reviews'][0]['note'], 'Private visitor note.')
        _, other, _ = self.request('/api/mission', cookie=second)
        self.assertEqual(other['demo_server']['scenario'], 'baseline')
        self.assertNotIn('Private visitor note.', json.dumps(other))

        status, draft, _ = self.request('/api/crew/draft', {
            'crew_id': 'AST-05', 'voice': 'calm', 'wearable': 'rest', 'scenario': 'baseline'}, cookie=second)
        self.assertEqual(status, 200)
        self.assertEqual(draft['crew_id'], 'AST-05')
        status, new, _ = self.request('/api/crew/checkin', {
            'crew_id': 'AST-05', 'draft_id': draft['draft_id']}, cookie=second)
        self.assertEqual(status, 200)
        self.assertEqual(new['member_entries']['AST-05'][0]['member']['crew_id'], 'AST-05')
        _, unchanged, _ = self.request('/api/mission', cookie=first)
        self.assertEqual(unchanged['member_entries']['AST-05'], first_entries)

    def test_disables_uploads_and_limits_writes(self):
        cookie = self.new_session()
        status, data, _ = self.request('/api/lab/test', {'kind': 'voice', 'sample': 'upload'}, cookie=cookie)
        self.assertEqual(status, 403)
        self.assertIn('disabled', data['error'])
        status, data, _ = self.request('/api/lab/test', {'kind': 'wearable', 'sample': 'upload', 'signals': {}}, cookie=cookie)
        self.assertEqual(status, 403)
        status, data, _ = self.request('/api/lab/test', {'kind': 'wearable', 'sample': 'rest'}, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(data['origin'], 'synthetic')
        with patch('backend.public_sessions.MAX_WRITES_PER_MINUTE', 1):
            status, _, _ = self.request('/api/demo/run', {'scenario': 'invalid'}, cookie=cookie)
            self.assertEqual(status, 429)

    def test_capacity_and_reuse(self):
        cookie = self.new_session()
        with patch('backend.public_sessions.MAX_SESSIONS', 1):
            status, _, _ = self.request('/api/session', {})
            self.assertEqual(status, 503)
            status, _, _ = self.request('/api/session', {}, cookie=cookie)
            self.assertEqual(status, 200)


class PublicConfigurationTests(unittest.TestCase):
    def test_rejects_insecure_or_malformed_origin(self):
        for url in ('', 'http://example.com', 'https://example.com:8443',
                    'https://example.com/path', 'https://name@example.com',
                    'https://example.com?x=1'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                configured_public_origin(url)
        self.assertEqual(configured_public_origin(ORIGIN), ORIGIN)
