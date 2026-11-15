import tempfile
import unittest
from pathlib import Path
from backend.demo_engine import DemoEngine

class ConnectedCheckinTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.engine=DemoEngine(Path(self.temp.name)/'checkin.sqlite3',Path(__file__).resolve().parents[1]/'models/wearable/model.json')
    def tearDown(self):self.temp.cleanup()
    def test_member_flags_and_cabin_association(self):
        choices={'AST-01':{'voice':'aroused','wearable':'elevated'},'AST-02':{'voice':'aroused','wearable':'elevated'}}
        self.engine.run('co2_rise',checkins=choices)
        view=self.engine.bundle();report=view['overview']['current_analysis']['report']
        codes=[f['code'] for f in report['findings']]
        self.assertIn('BOTH_INDICATORS_ELEVATED',codes)
        self.assertIn('POSSIBLE_ENVIRONMENTAL_ASSOCIATION',codes)
        self.assertEqual(view['overview']['snapshot']['payload']['crew_checkins'],choices)
        self.assertEqual(report['multimodal'][0]['crew_id'],'AST-01')
        self.assertEqual(report['multimodal'][1]['crew_id'],'AST-02')
    def test_disagreement_missing_and_nasa(self):
        self.engine.run('baseline',checkins={'AST-01':{'voice':'calm','wearable':'elevated'},'AST-02':{'voice':'silence','wearable':'missing'},'AST-03':{'voice':'artemis-terminator','wearable':'rest'}})
        report=self.engine.bundle()['overview']['current_analysis']['report']
        self.assertIn('MODALITY_DISAGREEMENT',[f['code'] for f in report['findings']])
        rows={r['crew_id']:r for r in report['multimodal']}
        self.assertIsNone(rows['AST-02']['signals']['voice']['stress_score'])
        self.assertIsNone(rows['AST-03']['signals']['voice']['stress_score'])
        self.assertIn('NASA_features_only',str(rows['AST-03']))
    def test_bad_identity_is_rejected(self):
        with self.assertRaises(ValueError):self.engine.run('baseline',checkins={'OTHER':{'voice':'calm','wearable':'rest'}})
