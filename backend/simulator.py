"""Repeatable synthetic input fixture, not an approved integration contract."""

import argparse
import json
import random
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.storage import DEFAULT_DATABASE, SnapshotStore
from backend.crew import demo_profiles
from backend.cabin import CabinConfig, co2_percent_after


def baseline_snapshot(crew_count=5):
    """Return fresh illustrative readings; no medical normality is implied.

    Values are demo choices, not measured data or validated personal baselines.
    Model outputs and assessments remain unavailable rather than fabricated.
    The timestamp belongs to the enclosing storage record for this fixture.
    """
    return {
        "scenario": "baseline_demo",
        "fixture_version": "internal-v1",
        "data_origin": "synthetic",
        "limitations": [
            "Illustrative values only; not clinical thresholds or astronaut data.",
            "No voice or wearable model has run; no assessment is available.",
            "Internal fixture layout; team integration contract is pending.",
        ],
        "mission_day": 142,
        "crew": [
            {
                "crew_id": profile["crew_id"],
                "data_origin": "synthetic",
                "biometrics": dict(profile["baseline"]),
                "voice": None,
                "wearable_inference": None,
                "assessment": None,
            }
            for profile in demo_profiles(crew_count)
        ],
        "environment": {
            "data_origin": "synthetic",
            "co2_percent": 0.10,
            "o2_percent": 21.0,
            "pressure_kpa": 101.0,
        },
    }


def save_baseline(store, timestamp):
    """Append one fixture through the existing storage interface."""
    return store.save_synthetic(timestamp, baseline_snapshot())


SCENARIOS = ("baseline", "co2_rise", "missing_sensor", "faulty_sensor")


def generate_scenario(scenario="baseline", *, seed=42, steps=12, crew_count=5,
                      cabin_config=None):
    """Generate one-minute demo samples with deterministic bounded jitter.

    Scripted crew changes are NOT a dose-response model for CO2. Sensor quality
    is fixture ground truth, not a fault diagnosis made by an algorithm.
    See SCENARIOS.md for sources and the assumptions behind these values.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {SCENARIOS}")
    if type(steps) is not int or not 2 <= steps <= 1440:
        raise ValueError("steps must be an integer between 2 and 1440")
    rng = random.Random(seed)
    demo_profiles(crew_count)  # Validate before generating any samples.
    cabin_config = CabinConfig() if cabin_config is None else cabin_config
    samples = []
    for index in range(steps):
        snapshot = baseline_snapshot(crew_count)
        snapshot.update(scenario=scenario, fixture_version="internal-v3",
                        seed=seed, elapsed_seconds=index * 60)
        snapshot["limitations"].append(
            "Noise and scripted trends are engineering assumptions, not a physiological model."
        )
        progress = max(0, (index / (steps - 1) - 0.25) / 0.75)
        for member in snapshot["crew"]:
            values = member["biometrics"]
            values["heart_rate_bpm"] += rng.randint(-2, 2)
            values["hrv_rmssd_ms"] += rng.randint(-2, 2)
            values["eda_microsiemens"] = round(
                values["eda_microsiemens"] + rng.uniform(-0.05, 0.05), 3)
            member["sensor_quality"] = {key: "available" for key in values}
            if scenario == "co2_rise":
                # Deliberately co-scripted to exercise correlation logic, not causation.
                values["heart_rate_bpm"] += round(18 * progress)
                values["hrv_rmssd_ms"] -= round(10 * progress)
                values["eda_microsiemens"] = round(
                    values["eda_microsiemens"] + 0.8 * progress, 3)
        environment = snapshot["environment"]
        environment["co2_percent"] = round(
            0.10 + rng.uniform(-0.005, 0.005), 4)
        environment["o2_percent"] = round(21.0 + rng.uniform(-0.02, 0.02), 3)
        environment["pressure_kpa"] = round(101.0 + rng.uniform(-0.05, 0.05), 3)
        if scenario == "co2_rise":
            # Balanced before the first quarter; removal then drops to configured level.
            seconds_since_change = max(0.0, index * 60 - (steps - 1) * 60 * 0.25)
            environment["co2_percent"] = round(
                co2_percent_after(seconds_since_change, crew_count, cabin_config), 6)
            environment["pressure_kpa"] = cabin_config.pressure_kpa
            snapshot["cabin_model"] = {
                "version": "trace-balance-v1",
                "parameters": asdict(cabin_config),
                "seconds_since_removal_change": seconds_since_change,
                "limitations": "Synthetic well-mixed constant-pressure approximation; no symptom prediction.",
            }
        snapshot["environment_quality"] = {
            key: "available" for key in ("co2_percent", "o2_percent", "pressure_kpa")
        }
        if index >= steps // 2 and scenario == "missing_sensor":
            environment["co2_percent"] = None
            snapshot["environment_quality"]["co2_percent"] = "missing"
            snapshot["crew"][0]["biometrics"]["eda_microsiemens"] = None
            snapshot["crew"][0]["sensor_quality"]["eda_microsiemens"] = "missing"
        if index >= steps // 2 and scenario == "faulty_sensor":
            # Negative bpm is an injected invalid reading, not a plausible pulse.
            snapshot["crew"][0]["biometrics"]["heart_rate_bpm"] = -10
            snapshot["crew"][0]["sensor_quality"]["heart_rate_bpm"] = "invalid"
        samples.append(snapshot)
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--scenario", choices=SCENARIOS, default="baseline")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--crew-count", type=int, default=5)
    parser.add_argument("--cabin-volume-m3", type=float, default=100.0)
    parser.add_argument("--removal-fraction", type=float, default=0.0)
    arguments = parser.parse_args()
    try:
        samples = generate_scenario(arguments.scenario, seed=arguments.seed,
                                    steps=arguments.steps, crew_count=arguments.crew_count,
                                    cabin_config=CabinConfig(volume_m3=arguments.cabin_volume_m3,
                                                             removal_fraction=arguments.removal_fraction))
    except ValueError as error:
        parser.error(str(error))
    store = SnapshotStore(arguments.database)
    store.initialize()
    store.register_synthetic_profiles(demo_profiles(arguments.crew_count))
    # Historical timestamps keep the final sample at now, never in the future.
    start = datetime.now(timezone.utc) - timedelta(minutes=len(samples) - 1)
    for sample in samples:
        timestamp = (start + timedelta(seconds=sample["elapsed_seconds"])).isoformat()
        store.save_synthetic(timestamp, sample)
    print(f"Appended {len(samples)} SYNTHETIC {arguments.scenario} snapshots to {store.path}")
    print(json.dumps(store.latest(), indent=2))


if __name__ == "__main__":
    main()
