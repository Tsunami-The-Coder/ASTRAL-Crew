"""Behavior and contract tests; no synthetic benchmark claims. AI-assisted."""
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from models.wearable.inference import assess, build_baseline, load_model, FEATURES
from models.wearable.demo import event, baseline_for, fixture_model, scenarios

CLOCK = "2026-11-14T14:30:00Z"


class InferenceTests(unittest.TestCase):
    def test_fifth_member_is_scored_with_own_baseline(self):
        model = load_model(Path(__file__).with_name("model.json"))
        result = self.score(event("AST-05"), model=model, baseline=baseline_for("AST-05"))
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["crew_id"], "AST-05")
        self.assertEqual(result["baseline"]["status"], "available")
        wrong = self.score(event("AST-05"), model=model, baseline=baseline_for("AST-01"))
        self.assertEqual(wrong["baseline"]["status"], "invalid")
        self.assertIsNone(self.score(event("AST-05", eda_microsiemens=None), model=model)["stress_score"])

    def test_unknown_crew_still_rejected(self):
        for crew in ("AST-00", "AST-06", "AST-5", "", None):
            self.assertEqual(self.score(event(crew))["status"], "invalid")

    def score(self, reading=None, **kwargs):
        return assess(event() if reading is None else reading, now=CLOCK, **kwargs)

    def test_no_model_does_not_fabricate_score(self):
        result = self.score()
        self.assertEqual(result["status"], "model_unavailable")
        self.assertIsNone(result["stress_score"])

    def test_synthetic_fixture_is_labelled(self):
        result = self.score(model=fixture_model())
        self.assertEqual(result["inference_origin"], "simulated_inference")
        self.assertEqual(result["data_origin"], "synthetic")
        self.assertIsNone(result["confidence"])
        self.assertTrue(0 <= result["stress_score"] <= 1)

    def test_each_missing_signal_is_not_normal(self):
        for key in FEATURES:
            reading = event(**{key: None})
            result = self.score(reading, model=fixture_model())
            self.assertEqual(result["status"], "missing", key)
            self.assertIsNone(result["stress_score"])

    def test_bad_values(self):
        for value in [float("nan"), float("inf"), True, "70", -1, 10000]:
            with self.subTest(value=value):
                result = self.score(event(heart_rate_bpm=value), model=fixture_model())
                self.assertEqual(result["status"], "invalid")
                json.dumps(result, allow_nan=False)

    def test_invalid_dominates_missing(self):
        result = self.score(event(heart_rate_bpm=-1, eda_microsiemens=None))
        self.assertEqual(result["status"], "invalid")

    def test_non_object_biometrics(self):
        reading = event(); reading["biometrics"] = []
        self.assertEqual(self.score(reading)["status"], "invalid")

    def test_timezones_and_normalization(self):
        reading = event(); reading.update(timestamp="2026-11-14T15:30:00+01:00", window_start="2026-11-14T15:29:00+01:00")
        result = self.score(reading)
        self.assertEqual(result["timestamp"], CLOCK)
        self.assertEqual(result["status"], "model_unavailable")

    def test_naive_missing_future_and_short_windows(self):
        for update in [{"timestamp": "2026-11-14T14:30:00"}, {"window_start": None},
                       {"timestamp": "2026-11-14T14:31:00Z"}, {"window_start": "2026-11-14T14:29:30Z"}]:
            reading = event(); reading.update(update)
            self.assertEqual(self.score(reading)["status"], "invalid")

    def test_stale(self):
        result = self.score(event(end="2026-11-14T14:20:00Z"), model=fixture_model())
        self.assertEqual(result["status"], "stale")
        self.assertIsNone(result["stress_score"])

    def test_no_origin_is_not_synthetic_by_default(self):
        reading = event(); del reading["data_origin"]
        self.assertEqual(self.score(reading)["status"], "invalid")

    def test_malformed_identifiers_return_invalid(self):
        reading = event(); reading.update(crew_id=[], data_origin={})
        self.assertEqual(self.score(reading)["status"], "invalid")

    def test_research_model_rejects_unknown_feature_semantics(self):
        model = fixture_model(); model.update(training_data_origin="research", feature_pipeline="specific-v1")
        self.assertEqual(self.score(model=model)["status"], "incompatible_features")

    def test_research_model_rejects_different_window_length(self):
        model = fixture_model(); model.update(training_data_origin="research", feature_pipeline="wrist-bvp-eda-acc-60s-v1")
        reading = event(); reading["window_start"] = "2026-11-14T14:28:00Z"
        self.assertEqual(self.score(reading, model=model)["status"], "incompatible_features")

    def test_no_input_mutation(self):
        reading = event(); original = copy.deepcopy(reading)
        self.score(reading, model=fixture_model(), baseline=baseline_for("AST-01"))
        self.assertEqual(reading, original)

    def test_motion_caution(self):
        self.assertEqual(self.score(event(motion_level=0.9))["quality"]["status"], "motion_caution")

    def test_explanations_and_sources_survive_unavailable_model(self):
        result = self.score(baseline=baseline_for("AST-01"))
        self.assertTrue(any("No stress estimate" in text for text in result["explanation"]))
        self.assertTrue(any("reference" in text for text in result["explanation"]))
        self.assertTrue({"NASA-HAZARDS", "NASA-RISKS", "CSA-RADIATION"} <= set(result["evidence_ids"]))
        self.assertTrue(all(source["url"].startswith("https://") for source in result["evidence"]))

    def test_context_does_not_change_score(self):
        reading = event(); reading["context"] = {"sleep_hours": 2, "self_report_stress_0_10": 10}
        result = self.score(reading, model=fixture_model())
        self.assertEqual(result["stress_score"], self.score(model=fixture_model())["stress_score"])
        self.assertEqual(result["context"]["sleep_hours"], 2)

    def test_invalid_context_is_ignored(self):
        reading = event(); reading["context"] = {"sleep_hours": -1}
        result = self.score(reading)
        self.assertEqual(result["context"], {})
        self.assertIn("ignored invalid context: sleep_hours", result["quality"]["issues"])

    def test_model_feature_order_and_scales_rejected(self):
        for update in [{"features": list(reversed(FEATURES))}, {"scale": [0, 1, 1, 1]},
                       {"weights": [float("nan")] * 4}, {"intercept": None}, {"training_data_origin": []}]:
            model = fixture_model(); model.update(update)
            self.assertEqual(self.score(model=model)["status"], "model_invalid")

    def test_model_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "model.json"
            path.write_text(json.dumps(fixture_model()), encoding="utf-8")
            self.assertEqual(self.score(model=load_model(path)), self.score(model=fixture_model()))

    def test_baseline_deltas(self):
        result = self.score(event(heart_rate_bpm=90), baseline=baseline_for("AST-01"))
        self.assertEqual(result["baseline"]["status"], "available")
        self.assertEqual(result["observations"][0]["delta"], 20)

    def test_wrong_crew_or_origin_baseline_rejected(self):
        for key, value in [("crew_id", "AST-02"), ("data_origin", "measured"), ("window_count", 2), ("end", CLOCK)]:
            baseline = baseline_for("AST-01"); baseline[key] = value
            self.assertEqual(self.score(baseline=baseline)["baseline"]["status"], "invalid")

    def test_duplicate_windows_are_not_baseline_evidence(self):
        with self.assertRaises(ValueError):
            build_baseline([event()] * 5)

    def test_insufficient_baseline(self):
        with self.assertRaises(ValueError):
            build_baseline([event()])

    def test_mixed_person_baseline(self):
        readings = [event(end=f"2026-11-14T14:{i:02}:00Z") for i in range(20, 25)]
        readings[0]["crew_id"] = "AST-02"
        with self.assertRaises(ValueError):
            build_baseline(readings)

    def test_demo_all_scenarios_and_json(self):
        cases = scenarios()
        self.assertEqual(len(cases), 5)
        self.assertTrue(all(len(case["wearable_results"]) == 5 for case in cases))
        self.assertEqual(cases[3]["wearable_results"][1]["status"], "missing")
        self.assertTrue(cases[4]["voice_mocks"])
        json.dumps(cases, allow_nan=False)


try:
    import numpy as np
    from models.wearable.signals import extract_window
    from models.wearable.train import window_label, subject_folds, evaluate
    HAS_TRAINING = True
except ImportError:
    HAS_TRAINING = False


@unittest.skipUnless(HAS_TRAINING, "optional training dependencies unavailable")
class TrainingTests(unittest.TestCase):
    def test_single_class_test_participant_is_retained_and_marked(self):
        rows = [{"subject_id": f"S{s}", "label": label,
                 "features": dict(zip(FEATURES, [70+label*20+s, 50, 2+label, 0.1]))}
                for s in (2, 3, 4) for label in ((0,) if s == 2 else (0, 1)) for _ in range(3)]
        _, report = evaluate(rows)
        self.assertEqual(report["n_subjects"], 3)
        self.assertEqual(report["balanced_accuracy_evaluable_subjects"], 2)
        self.assertIsNone(next(f for f in report["folds"] if f["held_out_subject"] == "S2")["balanced_accuracy"])
        self.assertEqual(sum(map(sum, report["pooled_confusion_matrix"])), len(rows))

    def test_secondary_peaks_are_rejected_instead_of_double_counted(self):
        time = np.arange(3840) / 64
        signal = np.sin(2*np.pi*time) + np.sin(4*np.pi*time)
        with self.assertRaisesRegex(ValueError, "periodicity"):
            extract_window(signal, np.ones(240)*2, np.tile([0, 0, 64], (1920, 1)))

    def test_clean_rate_range_survives_quality_gate(self):
        time = np.arange(3840) / 64
        for bpm in (45, 60, 90, 120, 150, 180):
            with self.subTest(bpm=bpm):
                result = extract_window(np.sin(2*np.pi*bpm/60*time), np.ones(240)*2,
                                        np.tile([0, 0, 64], (1920, 1)))
                self.assertAlmostEqual(result["heart_rate_bpm"], bpm, delta=2)

    def test_known_pulse_train(self):
        time = np.arange(3840) / 64
        result = extract_window(np.sin(2*np.pi*time), np.ones(240)*2, np.tile([0, 0, 64], (1920, 1)))
        self.assertAlmostEqual(result["heart_rate_bpm"], 60, delta=1)
        self.assertLess(result["hrv_rmssd_ms"], 30)
        self.assertEqual(result["motion_level"], 0)

    def test_bad_raw_signals(self):
        for bvp in [np.zeros(3840), np.full(3840, np.nan), np.ones(20)]:
            with self.assertRaises(ValueError):
                extract_window(bvp, np.ones(240), np.zeros((1920, 3)))

    def test_label_mapping_and_transition_exclusion(self):
        for label, expected in [(1, 0), (2, 1), (3, 0), (0, None), (4, None), (5, None)]:
            self.assertEqual(window_label(np.full(42000, label)), expected)
        self.assertIsNone(window_label(np.r_[np.ones(21000), np.ones(21000)*2]))

    def test_no_participant_leakage(self):
        groups = np.array(["S2", "S2", "S3", "S3", "S4", "S4"])
        for subject, train, test in subject_folds(groups):
            self.assertTrue(set(groups[train]).isdisjoint(groups[test]))
            self.assertEqual(set(groups[test]), {subject})

    def test_exported_inference_agrees_with_sklearn(self):
        rows = [{"subject_id": f"S{s}", "label": label,
                 "features": dict(zip(FEATURES, [70+label*20+s, 50-label*20, 2+label*3, 0.1]))}
                for s in [2, 3, 4] for label in [0, 1] for _ in range(3)]
        model, report = evaluate(rows)
        # Engineering fixture only: these metrics are never reported as research validation.
        self.assertEqual(report["n_subjects"], 3)
        self.assertEqual(len(report["folds"]), 3)
        from models.wearable.train import _pipeline
        x = [[r["features"][key] for key in FEATURES] for r in rows]
        fitted = _pipeline().fit(x, [r["label"] for r in rows])
        reading = event()
        expected = fitted.predict_proba([[reading["biometrics"][key] for key in FEATURES]])[0, 1]
        result = assess(reading, model=model, now=CLOCK)
        self.assertAlmostEqual(result["stress_score"], expected, places=5)


if __name__ == "__main__":
    unittest.main()
