"""Wearable-only engineering scenarios, not simulated human physiology or training data.

AI-assisted. Scenario numbers are arbitrary fixtures, not NASA-derived effects.
No environmental sensors, voice fusion, medical rules or app integration.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
from .demo import event, baseline_for
from .inference import assess, load_model

CLOCK = "2026-11-14T14:30:00Z"


def scenarios(model):
    definitions = [
        ("reference", "reference", "Display a research indicator and comparable personal observations."),
        ("sleep_context", "isolation_and_confinement", "Display sleep/self-report without inventing trained sleep effects."),
        ("exercise", "gravity_fields", "Flag motion; an exercise response does not establish psychological stress."),
        ("changed_reading", "gravity_fields", "Display a personal delta; its cause and any gravity correction remain unknown."),
        ("radiation_blind_spot", "space_radiation", "Unchanged wrist readings cannot establish absence of radiation exposure."),
        ("habitat_blind_spot", "hostile_closed_environment", "Wrist readings cannot measure air quality or identify a habitat-related cause."),
        ("delayed_reading", "distance_from_earth", "Evaluate locally; an old observation must remain stale at receipt time."),
        ("missing_sensor", "sensor_quality", "Keep a missing measurement and its stress score unavailable."),
        ("incompatible_reference", "measurement_comparability", "Reject reference deltas from a different extraction pipeline."),
    ]
    cases = []
    for name, hazard, expected in definitions:
        reading = event()
        baseline = baseline_for("AST-01")
        if name == "sleep_context":
            reading["context"] = {"sleep_hours": 4, "self_report_stress_0_10": 7}
        elif name == "exercise":
            reading["biometrics"].update(heart_rate_bpm=110, motion_level=0.85)
        elif name == "changed_reading":
            reading["biometrics"]["heart_rate_bpm"] = 90
        elif name == "delayed_reading":
            reading = event(end="2026-11-14T14:00:00Z")
            baseline = None
        elif name == "missing_sensor":
            reading["biometrics"]["eda_microsiemens"] = None
        elif name == "incompatible_reference":
            baseline["feature_pipeline"] = "different-sensor-method"
        cases.append({"scenario": name, "hazard_or_test_topic": hazard,
                      "data_origin": "synthetic", "ai_assisted": True,
                      "expected_behavior": expected, "input": copy.deepcopy(reading),
                      "baseline_input": baseline, "clock": CLOCK,
                      "result": assess(reading, model=model, baseline=baseline, now=CLOCK)})
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path(__file__).with_name("model.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"purpose": "Software behavior checks; not spaceflight accuracy or a physiological simulator",
              "training_data_created": False, "scenarios": scenarios(load_model(args.model))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Wrote {len(report['scenarios'])} wearable-only synthetic scenarios to {args.output}")


if __name__ == "__main__":
    main()
