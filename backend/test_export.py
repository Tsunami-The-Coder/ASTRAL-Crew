import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from backend.export import export_bundle
from backend.crew import demo_profiles
from backend.multimodal import analyze_multimodal
from backend.service import MissionService
from backend.simulator import generate_scenario


class ExportTests(unittest.TestCase):
    def test_empty_export_is_explicit_and_json_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            service=MissionService(Path(directory)/'mission.sqlite3')
            service.initialize()
            bundle=export_bundle(service)
            self.assertIsNone(bundle['overview']['snapshot'])
            self.assertEqual(bundle['snapshot_history'],[])
            self.assertEqual(bundle['medical_resources']['availability'],'no_reviewed_content')
            json.dumps(bundle,allow_nan=False)

    def test_export_preserves_findings_reviews_and_freshness_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            clock=datetime(2026,11,15,12,tzinfo=timezone.utc)
            service=MissionService(Path(directory)/'mission.sqlite3',clock=lambda:clock)
            service.initialize()
            profiles=demo_profiles()
            service.store.register_synthetic_profiles(profiles)
            samples=generate_scenario('co2_rise')
            samples[0]['run_id']=samples[-1]['run_id']='test-run'
            first=service.store.save_synthetic((clock-timedelta(minutes=11)).isoformat(),samples[0])
            last=service.store.save_synthetic(clock.isoformat(),samples[-1])
            report=analyze_multimodal(samples[-1],profiles,previous=samples[0],
                                     snapshot_timestamp=clock.isoformat(),now=clock.isoformat())
            identifier=service.log.save_analysis(last,report,previous_snapshot_id=first)
            service.record_review(identifier,reviewer='Demo',decision='follow_up',note='Synthetic test.')
            before=service.store.history()
            bundle=export_bundle(service,limit=2)
            self.assertEqual(bundle['overview']['current_analysis']['report'],report)
            self.assertEqual(len(bundle['mission_logs'][0]['reviews']),1)
            self.assertEqual(service.store.history(),before)
            service.clock=lambda:clock+timedelta(minutes=10)
            historical=export_bundle(service)
            self.assertIsNone(historical['overview']['current_analysis'])
            self.assertIsNotNone(historical['overview']['historical_analysis'])
            self.assertEqual(historical['overview']['freshness']['status'],'stale')
            json.dumps(historical,allow_nan=False)
