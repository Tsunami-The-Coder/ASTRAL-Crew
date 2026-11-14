"""Integration checks using disposable SQLite files and synthetic inputs."""

import tempfile
import unittest
from pathlib import Path

from backend.simulator import baseline_snapshot, save_baseline, generate_scenario, SCENARIOS
from backend.storage import SnapshotStore


class SimulatorTests(unittest.TestCase):
    def test_seed_reproduces_variation(self):
        samples = generate_scenario(seed=7)
        self.assertEqual(samples, generate_scenario(seed=7))
        self.assertNotEqual(samples, generate_scenario(seed=8))
        for sample in samples:
            for member in sample["crew"]:
                self.assertTrue(60 <= member["biometrics"]["heart_rate_bpm"] <= 100)
                self.assertIsNone(member["wearable_inference"])
                self.assertIsNone(member["voice"])

    def test_rise_and_sensor_cases(self):
        rising = generate_scenario("co2_rise")
        co2 = [sample["environment"]["co2_percent"] for sample in rising]
        self.assertEqual(co2, sorted(co2))
        self.assertEqual(co2[0], 0.1)
        self.assertGreater(co2[-1], co2[0])
        self.assertLess(co2[-1], 0.5)
        missing = generate_scenario("missing_sensor")
        self.assertIsNotNone(missing[0]["environment"]["co2_percent"])
        self.assertIsNone(missing[-1]["environment"]["co2_percent"])
        self.assertEqual(missing[-1]["environment_quality"]["co2_percent"], "missing")
        faulty = generate_scenario("faulty_sensor")[-1]["crew"][0]
        self.assertEqual(faulty["sensor_quality"]["heart_rate_bpm"], "invalid")
        self.assertLess(faulty["biometrics"]["heart_rate_bpm"], 0)

    def test_all_scenarios_persist_offline(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                store = SnapshotStore(Path(directory) / "test.sqlite3")
                store.initialize()
                samples = generate_scenario(scenario)
                for index, sample in enumerate(samples):
                    store.save_synthetic(f"2026-11-14T12:{index:02}:00Z", sample)
                self.assertEqual(store.latest()["payload"], samples[-1])

    def test_reject_invalid_configuration(self):
        with self.assertRaises(ValueError):
            generate_scenario("unknown")
        for steps in (0, 1, 1441, True, 2.5):
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                generate_scenario(steps=steps)

    def test_fixture_persists_without_inventing_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mission.sqlite3"
            store = SnapshotStore(path)
            store.initialize()
            first = save_baseline(store, "2026-11-14T12:00:00Z")
            second = save_baseline(store, "2026-11-14T12:01:00Z")
            self.assertNotEqual(first, second)
            result = SnapshotStore(path).latest()
            self.assertEqual(result["id"], second)
            self.assertEqual(result["data_origin"], "synthetic")
            self.assertEqual(result["payload"], baseline_snapshot())
            crew = result["payload"]["crew"]
            self.assertEqual([member["crew_id"] for member in crew],
                             ["AST-01", "AST-02", "AST-03", "AST-04", "AST-05"])
            for member in crew:
                self.assertIsNone(member["voice"])
                self.assertIsNone(member["wearable_inference"])
                self.assertIsNone(member["assessment"])

    def test_each_fixture_is_independent(self):
        snapshot = baseline_snapshot()
        snapshot["crew"][0]["biometrics"]["heart_rate_bpm"] = None
        snapshot["environment"]["co2_percent"] = None
        fresh = baseline_snapshot()
        self.assertEqual(fresh["crew"][0]["biometrics"]["heart_rate_bpm"], 68)
        self.assertEqual(fresh["environment"]["co2_percent"], 0.10)


if __name__ == "__main__":
    unittest.main()
