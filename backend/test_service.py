import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.crew import demo_profiles
from backend.cross_analysis import analyze_snapshot
from backend.service import MissionService
from backend.simulator import generate_scenario


class ServiceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'mission.sqlite3'
        self.service = MissionService(self.path, clock=lambda: datetime(2026,11,14,12,11,tzinfo=timezone.utc))
        self.service.initialize()

    def test_empty_without_invented_readings(self):
        view = self.service.overview()
        self.assertIsNone(view['snapshot'])
        self.assertIsNone(view['current_analysis'])
        self.assertEqual(view['analysis_status'], 'no_telemetry')
        self.assertEqual(self.service.crew_profiles(), [])
        self.assertEqual(self.service.mission_logs(), [])

    def populate(self, count=5):
        profiles = demo_profiles(count)
        self.service.store.register_synthetic_profiles(profiles)
        samples = generate_scenario('co2_rise', crew_count=count)
        first = self.service.store.save_synthetic('2026-11-14T12:00:00Z',samples[0])
        last = self.service.store.save_synthetic('2026-11-14T12:11:00Z',samples[-1])
        report = analyze_snapshot(samples[-1],profiles,previous=samples[0])
        return self.service.log.save_analysis(last,report,previous_snapshot_id=first)

    def test_matching_analysis_review_and_reopen(self):
        identifier = self.populate()
        self.service.record_review(identifier, reviewer='Demo reviewer',decision='follow_up',note='Verify inputs.')
        reopened = MissionService(self.path, clock=self.service.clock)
        view = reopened.overview()
        self.assertEqual(view['analysis_status'], 'available')
        self.assertEqual(view['current_analysis']['id'],identifier)
        self.assertEqual(len(view['current_analysis']['reviews']),1)
        self.assertEqual(len(view['snapshot']['payload']['crew']),5)
        self.assertIsNone(view['snapshot']['payload']['crew'][0]['voice'])

    def test_old_analysis_never_attached_to_new_readings(self):
        self.populate()
        self.service.store.save_synthetic('2026-11-14T12:12:00Z',generate_scenario()[-1])
        view = self.service.overview()
        self.assertIsNone(view['current_analysis'])
        self.assertEqual(view['analysis_status'],'not_run_for_latest_snapshot')
        self.assertEqual(len(self.service.mission_logs()),1)

    def test_crew_projection_preserves_missing_data_and_roster_changes(self):
        self.populate(4)
        self.assertEqual(self.service.crew_history('AST-05'),[])
        sample = generate_scenario('missing_sensor')[-1]
        self.service.store.save_synthetic('2026-11-14T12:12:00Z',sample)
        history = self.service.crew_history('AST-01',limit=1)
        self.assertEqual(len(history),1)
        self.assertIsNone(history[0]['crew']['biometrics']['eda_microsiemens'])
        self.assertEqual(len(self.service.crew_history('AST-05')),1)
        with self.assertRaises(ValueError):
            self.service.crew_history('')
