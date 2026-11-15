import unittest
import tempfile
from pathlib import Path
from backend.demo_engine import DemoEngine

class MemberEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.engine=DemoEngine(Path(self.tmp.name)/'mission.sqlite3',Path(__file__).resolve().parents[1]/'models/wearable/model.json')
    def tearDown(self):self.tmp.cleanup()
    def test_preloaded_entries_and_isolated_history(self):
        for index in range(1,6):
            row=self.engine.entries.history(f'AST-{index:02}')[0]
            self.assertEqual(row['kind'],'preloaded')
            self.assertIn('timestamp',row)
        initial=self.engine.entries.history('AST-02')
        draft=self.engine.entries.draft('AST-01','aroused','elevated','co2_rise')
        self.engine.entries.save('AST-01',draft['generated_at'],{'kind':'submitted','member':draft['member']})
        self.assertEqual(len(self.engine.entries.history('AST-01')),2)
        self.assertEqual(self.engine.entries.history('AST-02'),initial)
    def test_draft_identity_expiry_and_exact_readings(self):
        draft=self.engine.entries.draft('AST-01','aroused','elevated','baseline')
        with self.assertRaises(ValueError):self.engine.entries.get_draft(draft['draft_id'],'AST-02')
        self.engine.run('baseline',checkins={'AST-01':{'voice':'aroused','wearable':'elevated','draft_readings':draft['member']['biometrics']}})
        actual=self.engine.bundle()['overview']['snapshot']['payload']['crew'][0]['biometrics']
        self.assertEqual(actual,draft['member']['biometrics'])
        self.engine.entries.drafts[draft['draft_id']]['expires_at']='2000-01-01T00:00:00+00:00'
        with self.assertRaises(ValueError):self.engine.entries.get_draft(draft['draft_id'],'AST-01')
    def test_acted_recordings_are_not_stress_labels(self):
        self.engine.run('baseline',checkins={'AST-01':{'voice':'ravdess-fearful','wearable':'rest'}})
        voice=self.engine.bundle()['overview']['current_analysis']['report']['multimodal'][0]['signals']['voice']
        self.assertIsNone(voice['stress_score'])
        self.assertIn('RAVDESS_features_only',str(voice))
