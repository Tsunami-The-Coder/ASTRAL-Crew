"""Internal rules for synthetic fixtures; not a clinical or shared model API."""

import argparse
import json
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path

from backend.storage import DEFAULT_DATABASE, SnapshotStore


@dataclass(frozen=True)
class RuleConfig:
    """Editable demo deltas, not medical limits or NASA alarm thresholds."""

    heart_rate_increase_bpm: float = 10
    hrv_decrease_ms: float = 6
    eda_increase_microsiemens: float = 0.4
    co2_increase_percentage_points: float = 0.01
    minimum_changed_crew: int = 2
    radiation_rate_ratio: float = 2
    radiation_rate_increase_msv_per_day: float = 1

    def __post_init__(self):
        for key, value in asdict(self).items():
            if type(value) not in (int, float) or not isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be finite and positive")
        if type(self.minimum_changed_crew) is not int:
            raise ValueError("minimum_changed_crew must be an integer")
        if self.radiation_rate_ratio <= 1:
            raise ValueError("radiation_rate_ratio must exceed 1")


def _reading(values, quality, field, issues, scope):
    value = values.get(field)
    # Check the observed value independently of simulator ground-truth flags.
    if value is None:
        issues.append({"scope": scope, "field": field, "status": "missing"})
        return None
    if (type(value) not in (int, float) or not isfinite(value) or value < 0
            or (field == "heart_rate_bpm" and value == 0)
            or (field == "co2_percent" and value > 100)):
        issues.append({"scope": scope, "field": field, "status": "invalid"})
        return None
    if quality.get(field, "available") != "available":
        issues.append({"scope": scope, "field": field, "status": "unavailable"})
        return None
    return value



def _radiation_changes(snapshot, previous, config, issues):
    prior = {}
    if previous is not None:
        if not isinstance(previous, dict) or not isinstance(previous.get('crew'), list):
            raise ValueError('previous snapshot must contain a crew list')
        for member in previous['crew']:
            if not isinstance(member, dict):
                raise ValueError('previous crew entries must be objects')
            crew_id = member.get('crew_id')
            if not isinstance(crew_id, str) or not crew_id or crew_id in prior:
                raise ValueError('previous crew IDs must be unique nonempty strings')
            prior[crew_id] = member
    changes = []
    for member in snapshot['crew']:
        crew_id = member['crew_id']
        radiation = member.get('radiation')
        if radiation is None:
            radiation = {}
        if not isinstance(radiation, dict):
            raise ValueError('radiation must be an object or null')
        field = 'dose_equivalent_rate_msv_per_day'
        quality = {field: radiation.get('quality', 'available')}
        rate = _reading(radiation, quality, field, issues, crew_id + ':radiation')
        # Validate accumulated dose without interpreting missing career history.
        dose_field = 'dose_equivalent_since_run_start_msv'
        _reading(radiation, {dose_field: radiation.get('quality', 'available')},
                 dose_field, issues, crew_id + ':radiation')
        if previous is None:
            continue
        old_radiation = prior.get(crew_id, {}).get('radiation')
        if old_radiation is None:
            old_radiation = {}
        if not isinstance(old_radiation, dict):
            raise ValueError('previous radiation must be an object or null')
        old = _reading(old_radiation, {field: old_radiation.get('quality', 'available')},
                       field, issues, crew_id + ':previous_radiation')
        if rate is not None and old is not None:
            delta = rate - old
            if delta >= config.radiation_rate_increase_msv_per_day and rate >= old * config.radiation_rate_ratio:
                changes.append({'crew_id': crew_id, 'previous_rate_msv_per_day': old,
                                'current_rate_msv_per_day': rate,
                                'increase_msv_per_day': round(delta, 6)})
    return changes


def analyze_snapshot(snapshot, profiles, *, previous=None, config=RuleConfig()):
    """Compare current synthetic readings with supplied synthetic references.

    previous is an explicitly selected earlier snapshot from the SAME run.
    No scenario name or cabin-model parameters are used to infer a cause.
    Missing model outputs remain unavailable; they are not replaced by scores.
    Malformed structural inputs raise ValueError; bad readings become issues.
    """
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("crew"), list):
        raise ValueError("snapshot must contain a crew list")
    if not snapshot["crew"] or snapshot.get("data_origin") != "synthetic":
        raise ValueError("this internal analyzer requires nonempty synthetic fixtures")
    references = {}
    for profile in profiles:
        if not isinstance(profile, dict) or not isinstance(profile.get("baseline"), dict):
            raise ValueError("profiles must contain baseline objects")
        crew_id = profile.get("crew_id")
        if not isinstance(crew_id, str) or not crew_id or crew_id in references:
            raise ValueError("profile crew IDs must be unique nonempty strings")
        references[crew_id] = profile["baseline"]
    issues, crew_results, changed, seen = [], [], [], set()
    for member in snapshot["crew"]:
        if not isinstance(member, dict):
            raise ValueError("crew entries must be objects")
        crew_id = member.get("crew_id")
        if not isinstance(crew_id, str) or not crew_id or crew_id in seen:
            raise ValueError("snapshot crew IDs must be unique nonempty strings")
        seen.add(crew_id)
        values = member.get("biometrics") or {}
        quality = member.get("sensor_quality") or {}
        if not isinstance(values, dict) or not isinstance(quality, dict):
            raise ValueError("biometrics and sensor_quality must be objects or null")
        reference = references.get(crew_id, {})
        evidence = []
        for field, threshold, direction in (
            ("heart_rate_bpm", config.heart_rate_increase_bpm, 1),
            ("hrv_rmssd_ms", config.hrv_decrease_ms, -1),
            ("eda_microsiemens", config.eda_increase_microsiemens, 1),
        ):
            observed = _reading(values, quality, field, issues, crew_id)
            baseline = _reading(reference, {}, field, issues, crew_id + ":reference")
            if observed is not None and baseline is not None:
                delta = observed - baseline
                if direction * delta >= threshold:
                    evidence.append({"field": field, "observed": observed,
                                     "reference": baseline, "delta": round(delta, 6)})
        # Two independent feature comparisons are required by this demo rule.
        if len(evidence) >= 2:
            changed.append(crew_id)
        unavailable = [name for name in ("voice", "wearable_inference")
                       if member.get(name) is None]
        crew_results.append({"crew_id": crew_id, "changed": len(evidence) >= 2,
                             "evidence": evidence, "unavailable_models": unavailable})
    environment = snapshot.get("environment") or {}
    quality = snapshot.get("environment_quality") or {}
    if not isinstance(environment, dict) or not isinstance(quality, dict):
        raise ValueError("environment and environment_quality must be objects or null")
    co2 = _reading(environment, quality, "co2_percent", issues, "cabin")
    delta = None
    if previous is not None:
        if not isinstance(previous, dict):
            raise ValueError("previous snapshot must be an object")
        old_environment = previous.get("environment") or {}
        old_quality = previous.get("environment_quality") or {}
        if not isinstance(old_environment, dict) or not isinstance(old_quality, dict):
            raise ValueError("previous environment fields must be objects or null")
        old = _reading(old_environment, old_quality, "co2_percent", issues, "previous_cabin")
        if co2 is not None and old is not None:
            delta = round(co2 - old, 6)
    findings = []
    if len(changed) >= config.minimum_changed_crew:
        findings.append({"code": "SHARED_CREW_CHANGE", "crew_ids": changed,
                         "message": "Multiple crew readings differ from demo references; cause unresolved."})
        if delta is not None and delta >= config.co2_increase_percentage_points:
            findings.append({"code": "POSSIBLE_ENVIRONMENTAL_ASSOCIATION",
                             "co2_delta_percentage_points": delta,
                             "message": "Shared crew changes coincide with a CO2 rise. Review ventilation/removal and verify readings; causation is unconfirmed."})
    radiation_changes = _radiation_changes(snapshot, previous, config, issues)
    if radiation_changes:
        findings.append({"code": "RADIATION_RATE_INCREASE",
                         "evidence": radiation_changes,
                         "message": "Dose-equivalent rates increased from earlier readings. Verify dosimeters and request human review; cause is unconfirmed."})
    return {"rules_version": "demo-rules-v2", "data_origin": "simulated_inference",
            "config": asdict(config), "crew": crew_results, "input_issues": issues,
            "co2_delta_percentage_points": delta, "findings": findings,
            "needs_review": bool(findings or issues),
            "limitations": ["Demo thresholds, not clinical limits or validated stress classification.",
                            "Voice/wearable inference is not consumed yet; no fitness or safety conclusion.",
                            "No findings does not establish normal health or safe cabin conditions."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--save", action="store_true", help="Append the report to the local mission log")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("Database missing; generate a scenario first.")
    store = SnapshotStore(args.database)
    try:
        rows = store.history(limit=args.limit)
        if not rows:
            parser.error("No snapshots available.")
        # Each generator run has a unique timestamp minus elapsed_seconds anchor.
        # Avoid associating separate, potentially overlapping simulation runs.
        from datetime import datetime, timedelta
        anchors = {datetime.fromisoformat(row["timestamp"]) - timedelta(
            seconds=row["payload"].get("elapsed_seconds", 0)) for row in rows}
        if len(anchors) != 1:
            parser.error("Selected history mixes runs. Use a separate scenario database or smaller --limit.")
        report = analyze_snapshot(rows[-1]["payload"], store.crew_profiles(),
                                  previous=rows[0]["payload"] if len(rows) > 1 else None)
    except ValueError as error:
        parser.error(str(error))
    if args.save:
        from backend.mission_log import MissionLog
        log = MissionLog(args.database)
        log.initialize()
        identifier = log.save_analysis(rows[-1]["id"], report,
                                       previous_snapshot_id=rows[0]["id"] if len(rows) > 1 else None)
        print(f"Saved simulated analysis {identifier} to mission log.")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
