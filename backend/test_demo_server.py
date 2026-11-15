"""Local HTTP and actual-pipeline smoke checks on synthetic inputs only."""
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from backend.demo_engine import DemoEngine, SCENARIOS
from backend.demo_server import DemoServer


class DemoServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.engine = DemoEngine(Path(cls.directory.name) / 'demo.sqlite3', Path(__file__).resolve().parents[1] / 'models/wearable/model.json')
        cls.engine.run('baseline')
        cls.server = DemoServer(('127.0.0.1', 0), cls.engine, Path(__file__).resolve().parents[1] / 'ui')
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.directory.cleanup()

    def request(self, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=60)
        try:
            connection.request('GET' if body is None else 'POST', path,
                               body=json.dumps(body) if body is not None else None,
                               headers=headers or ({'Content-Type': 'application/json'} if body is not None else {}))
            response = connection.getresponse()
            data = response.read()
            return response.status, json.loads(data) if response.getheader('Content-Type', '').startswith('application/json') else data
        finally:
            connection.close()

    def test_health_and_existing_layout_served(self):
        status, data = self.request('/api/health')
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'ready')
        status, html = self.request('/astral-prototype/')
        self.assertEqual(status, 200)
        self.assertIn(b'crew-dashboard.js', html)
        status, csv = self.request('/data/OSD-575_CMP_TRANSFORMED.csv')
        self.assertEqual(status, 200)
        for path in ('/submission-assets/audio/manifest.json', '/submission-assets/audio/ravdess/manifest.json', '/submission-assets/data/wesad-model.json', '/submission-assets/audio/artemis-closest.wav'):
            status, payload = self.request(path)
            self.assertEqual(status, 200, path)
            self.assertTrue(payload, path)
        self.assertEqual(status, 200)

    def test_actual_models_to_api_and_persistent_review(self):
        status, data = self.request('/api/demo/run', {'scenario': 'disagreement'})
        self.assertEqual(status, 200)
        analysis = data['overview']['current_analysis']
        self.assertIn('MODALITY_DISAGREEMENT', [f['code'] for f in analysis['report']['findings']])
        snapshot = data['overview']['snapshot']
        request = {'analysis_id': analysis['id'], 'snapshot_id': snapshot['id'], 'run_id': snapshot['payload']['run_id'],
                   'reviewer': 'Demo tester', 'decision': 'follow_up', 'note': 'Synthetic test; verify the disagreement.'}
        status, reviewed = self.request('/api/reviews', request)
        self.assertEqual(status, 200)
        self.assertEqual(len(reviewed['mission_logs'][0]['reviews']), 1)
        reread = self.request('/api/mission')[1]
        self.assertEqual(reread['mission_logs'][0]['reviews'][0]['note'], request['note'])
        request['run_id'] = 'another-run'
        self.assertEqual(self.request('/api/reviews', request)[0], 400)

    def test_invalid_scenario_origin_and_host_rejected(self):
        self.assertEqual(self.request('/api/demo/run', {'scenario': 'invalid'})[0], 400)
        self.assertEqual(self.request('/api/demo/run', {'scenario': 'baseline'}, {'Origin': 'https://example.org', 'Content-Type': 'application/json'})[0], 403)
        self.assertEqual(self.request('/api/mission', headers={'Host': 'example.org'})[0], 403)

    def test_baseline_missing_motion_and_environment_are_distinct(self):
        cases = {'baseline': None, 'co2_rise': 'BOTH_INDICATORS_ELEVATED', 'exercise': 'MOVEMENT_CAUTION',
                 'radiation_rise': 'RADIATION_RATE_INCREASE', 'pressure_drop': 'CABIN_PRESSURE_DROP',
                 'oxygen_drop': 'CABIN_OXYGEN_FRACTION_DROP', 'missing_sensor': None, 'faulty_sensor': None}
        for scenario, expected in cases.items():
            with self.subTest(scenario=scenario):
                status, data = self.request('/api/demo/run', {'scenario': scenario})
                self.assertEqual(status, 200)
                report = data['overview']['current_analysis']['report']
                codes = [f['code'] for f in report['findings']]
                if expected:
                    self.assertIn(expected, codes)
                elif scenario == 'baseline':
                    self.assertEqual(codes, [])
                else:
                    self.assertTrue(report['input_issues'])
                self.assertEqual(len(data['snapshot_history']), 12)
                self.assertEqual(len(report['multimodal']), 5)
                fifth = report['multimodal'][-1]
                self.assertEqual(fifth['crew_id'], 'AST-05')
                self.assertEqual(fifth['status'], 'compared')
                self.assertEqual(fifth['signals']['voice']['status'], 'available')
                self.assertEqual(fifth['signals']['wearable']['status'], 'available')
                self.assertIn('AST-05', data['demo_server']['supported_model_crew'])

    def test_fifth_member_audio_and_checkin_are_supported(self):
        status, audio = self.request('/api/lab/audio/calm?crew_id=AST-05')
        self.assertEqual(status, 200)
        self.assertTrue(audio.startswith(b'RIFF'))

        status, draft = self.request('/api/crew/draft', {
            'crew_id': 'AST-05', 'voice': 'aroused', 'wearable': 'elevated', 'scenario': 'baseline'})
        self.assertEqual(status, 200)
        self.assertEqual(draft['crew_id'], 'AST-05')

        status, data = self.request('/api/crew/checkin', {
            'crew_id': 'AST-05', 'draft_id': draft['draft_id']})
        self.assertEqual(status, 200)
        self.assertEqual(data['member_entries']['AST-05'][0]['member']['crew_id'], 'AST-05')
        fifth = next(item for item in data['overview']['current_analysis']['report']['multimodal']
                     if item['crew_id'] == 'AST-05')
        self.assertEqual(fifth['status'], 'compared')
        self.assertEqual(fifth['signals']['voice']['status'], 'available')
        self.assertEqual(fifth['signals']['wearable']['status'], 'available')
        self.assertEqual(data['demo_server']['supported_model_crew'],
                         [f'AST-{i:02}' for i in range(1, 6)])

    def test_draft_submission_history_and_single_use(self):
        status, draft = self.request('/api/crew/draft', {'crew_id':'AST-01','voice':'aroused','wearable':'elevated','scenario':'baseline'})
        self.assertEqual(status,200)
        previous=len(self.request('/api/mission')[1]['member_entries']['AST-01'])
        self.assertEqual(self.request('/api/crew/checkin', {'crew_id':'AST-02','draft_id':draft['draft_id']})[0],400)
        status, data = self.request('/api/crew/checkin', {'crew_id':'AST-01','draft_id':draft['draft_id']})
        self.assertEqual(status,200)
        entries=data['member_entries']['AST-01']
        self.assertEqual(len(entries),previous+1)
        self.assertEqual(entries[0]['member']['biometrics'],draft['member']['biometrics'])
        self.assertEqual(entries[0]['analysis_id'],data['overview']['current_analysis']['id'])
        self.assertEqual(self.request('/api/crew/checkin', {'crew_id':'AST-01','draft_id':draft['draft_id']})[0],400)
        self.assertEqual(len(self.request('/api/mission')[1]['member_entries']['AST-01']),len(entries))

    def test_progress_matches_operation_and_saved_report(self):
        status, data = self.request('/api/mission/analyze', {'scenario':'baseline','operation_id':'progress-http-check'})
        self.assertEqual(status,200)
        status, progress = self.request('/api/progress')
        self.assertEqual(status,200)
        self.assertEqual(progress['operation_id'],'progress-http-check')
        self.assertEqual(progress['status'],'complete')
        self.assertTrue(all(s=='complete' for s in progress['steps'].values()))
        self.assertGreater(progress['elapsed_ms'],0)
        self.assertIsNotNone(data['overview']['current_analysis'])
        self.assertEqual(self.request('/api/mission/analyze',{'scenario':'invalid','operation_id':'bad-progress-check'})[0],400)
        self.assertEqual(self.request('/api/progress')[1]['status'],'failed')
