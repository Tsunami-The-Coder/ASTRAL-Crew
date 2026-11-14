import tempfile
import unittest
from pathlib import Path

from backend.gravity import GravityConfig, gravity_record
from backend.service import MissionService
from backend.simulator import generate_scenario


class GravityTests(unittest.TestCase):
    def test_educational_trend_and_unknown_measurements(self):
        self.assertEqual(gravity_record(0)['illustrative_bone_density_percent_of_start'],100)
        self.assertEqual(gravity_record(30)['illustrative_bone_density_percent_of_start'],99)
        self.assertEqual(gravity_record(180)['illustrative_bone_density_percent_of_start'],94)
        record = gravity_record(30,GravityConfig(0))
        self.assertEqual(record['illustrative_bone_density_percent_of_start'],100)
        self.assertIsNone(record['measured_bone_density_g_per_cm2'])
        self.assertIsNone(record['cardiovascular_assessment'])
        self.assertEqual(record['measurement_status'],'unavailable')

    def test_reject_out_of_domain_and_malformed_inputs(self):
        for days in (-1,181,None,True,float('nan')):
            with self.assertRaises(ValueError):
                gravity_record(days)
        for rate in (-1,2,True,float('inf')):
            with self.assertRaises(ValueError):
                GravityConfig(rate)

    def test_gravity_stays_fixed_during_short_scenario_for_all_crew(self):
        for count in (4,5):
            samples = generate_scenario('co2_rise',crew_count=count,microgravity_days=30)
            for sample in samples:
                for crew in sample['crew']:
                    self.assertEqual(crew['gravity'],gravity_record(30))

    def test_persistence_and_service_preserve_simulation_label(self):
        with tempfile.TemporaryDirectory() as folder:
            service = MissionService(Path(folder)/'mission.sqlite3')
            service.initialize()
            sample = generate_scenario(microgravity_days=30)[-1]
            service.store.save_synthetic('2026-11-14T12:00:00Z',sample)
            view = service.overview()
            self.assertEqual(len(view['snapshot']['payload']['crew']),5)
            record = service.crew_history('AST-05')[0]['crew']['gravity']
            self.assertEqual(record['data_origin'],'simulated_inference')
            self.assertEqual(record['illustrative_bone_density_percent_of_start'],99)
            self.assertIsNone(record['measured_bone_density_g_per_cm2'])
