"""Space-resource-inspired software checks, never astronaut validation. AI-assisted."""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch
from .demo import event, baseline_for
from .inference import assess, build_baseline, load_model
from .space_scenarios import CLOCK, scenarios


class SpaceContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load_model(Path(__file__).with_name("model.json"))

    def test_local_inference_and_all_hazard_scenarios(self):
        with patch("socket.socket", side_effect=AssertionError("network attempted")):
            cases = {c["scenario"]: c for c in scenarios(self.model)}
        self.assertEqual(len(cases), 9)
        self.assertTrue(all(c["data_origin"] == "synthetic" for c in cases.values()))
        self.assertTrue(all(c["result"]["confidence"] is None for c in cases.values()))
        normal = cases["reference"]["result"]
        self.assertEqual(normal["status"], "available")
        self.assertEqual(cases["sleep_context"]["result"]["stress_score"], normal["stress_score"])
        self.assertEqual(cases["exercise"]["result"]["quality"]["status"], "motion_caution")
        self.assertEqual(cases["changed_reading"]["result"]["observations"][0]["delta"], 20)
        for name in ("radiation_blind_spot", "habitat_blind_spot"):
            self.assertEqual(cases[name]["result"], normal)
        for name, status in (("delayed_reading", "stale"), ("missing_sensor", "missing")):
            self.assertEqual(cases[name]["result"]["status"], status)
            self.assertIsNone(cases[name]["result"]["stress_score"])
        self.assertEqual(cases["incompatible_reference"]["result"]["baseline"]["status"], "invalid")

    def test_reject_mixed_or_unknown_baseline_methods(self):
        readings = [event(end=f"2026-11-14T14:{m}:00Z") for m in range(20, 25)]
        for pipeline in ("ecg-rmssd", None, [], ""):
            changed = copy.deepcopy(readings)
            changed[0]["feature_pipeline"] = pipeline
            with self.subTest(pipeline=pipeline), self.assertRaises(ValueError):
                build_baseline(changed)

    def test_reject_mixed_window_lengths(self):
        readings = [event(end=f"2026-11-14T14:{m}:00Z") for m in range(20, 25)]
        readings[0]["window_start"] = "2026-11-14T14:18:00Z"
        with self.assertRaises(ValueError):
            build_baseline(readings)

    def test_incompatible_baselines_do_not_contaminate_score(self):
        plain = assess(event(), model=self.model, now=CLOCK)
        for key, value in (("feature_pipeline", "ecg"), ("feature_pipeline", None),
                           ("window_seconds", 120), ("window_seconds", None)):
            baseline = baseline_for("AST-01")
            baseline[key] = value
            result = assess(event(), model=self.model, baseline=baseline, now=CLOCK)
            self.assertEqual(result["baseline"]["status"], "invalid")
            self.assertEqual(result["stress_score"], plain["stress_score"])
            self.assertTrue(all("delta" not in v for v in result["observations"]))

    def test_hazard_labels_cannot_change_prediction(self):
        original = event()
        expected = assess(original, model=self.model, now=CLOCK)
        for hazard in ("radiation", "microgravity", "isolation", "closed_habitat", "distance"):
            reading = copy.deepcopy(original)
            reading["hazard"] = hazard
            self.assertEqual(assess(reading, model=self.model, now=CLOCK), expected)


if __name__ == "__main__":
    unittest.main()
