"""Synthetic roster persistence and compatibility checks."""

import tempfile
import unittest
from pathlib import Path

from backend.crew import demo_profiles
from backend.simulator import generate_scenario
from backend.storage import SnapshotStore


class CrewTests(unittest.TestCase):
    def test_four_and_five_supported_in_every_scenario(self):
        for count in (4, 5):
            for scenario in ("baseline", "co2_rise", "missing_sensor", "faulty_sensor"):
                for snapshot in generate_scenario(scenario, crew_count=count):
                    self.assertEqual([member["crew_id"] for member in snapshot["crew"]],
                                     [profile["crew_id"] for profile in demo_profiles(count)])

    def test_reopen_idempotence_and_protected_baselines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "crew.sqlite3"
            store = SnapshotStore(path)
            store.initialize()
            self.assertEqual(store.crew_profiles(), [])
            profiles = demo_profiles()
            store.register_synthetic_profiles(profiles)
            store.register_synthetic_profiles(profiles)
            self.assertEqual(SnapshotStore(path).crew_profiles(), profiles)
            changed = demo_profiles()
            changed[0]["baseline"]["heart_rate_bpm"] = 99
            with self.assertRaises(ValueError):
                store.register_synthetic_profiles(changed)
            self.assertEqual(store.crew_profiles(), profiles)

    def test_batch_conflict_rolls_back_new_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory) / "crew.sqlite3")
            store.initialize()
            profiles = demo_profiles()
            store.register_synthetic_profiles(profiles[:1])
            profiles[0]["baseline"]["heart_rate_bpm"] = 99
            with self.assertRaises(ValueError):
                store.register_synthetic_profiles([profiles[1], profiles[0]])
            self.assertEqual(store.crew_profiles(), demo_profiles()[:1])

    def test_reject_invalid_count(self):
        for count in (0, 6, True, 2.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                demo_profiles(count)
