"""Offline inference on window summaries; no clinical or flight certification.

AI-assisted code. The handoff is a wearable-owned proposal, not a shared API.
NASA references motivate design, not numerical thresholds or learned weights.
"""
from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from .evidence import REFERENCES, explain

FEATURES = ("heart_rate_bpm", "hrv_rmssd_ms", "eda_microsiemens", "motion_level")
BOUNDS = ((20, 240), (0, 500), (0, 100), (0, 1))
ORIGINS = {"synthetic", "research", "replayed", "measured"}
SOURCE_IDS = ["NASA-STRESS-1160", "NASA-ARCHER", "NASA-STANDARD-MEASURES",
              "NASA-HAZARDS", "NASA-RISKS", "CSA-RADIATION"]
LIMITATIONS = [
    "Research prototype; not a diagnosis or medical device.",
    "Physiological activation does not identify its cause.",
    "No astronaut validation; NASA resources do not validate this algorithm.",
    "These wrist features cannot measure radiation dose, bone loss, immune changes or cabin air quality.",
    "Spaceflight physiology may differ from WESAD; no spaceflight correction has been validated.",
    "Raw pulse extraction rejects detected periodicity disagreements; summary inputs cannot prove raw signal quality. Pulse rate and RMSSD still need reference validation.",
]


def _time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO 8601 string with timezone")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp requires timezone")
    return result.astimezone(timezone.utc)


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _values(biometrics):
    if not isinstance(biometrics, dict):
        return None, ["biometrics must be an object"], "invalid"
    missing = [key for key in FEATURES if biometrics.get(key) is None]
    invalid = [key for key, (low, high) in zip(FEATURES, BOUNDS)
               if biometrics.get(key) is not None and
               (not _number(biometrics[key]) or not low <= biometrics[key] <= high)]
    if invalid:
        return None, ["invalid: " + ", ".join(invalid)], "invalid"
    if missing:
        return None, ["missing: " + ", ".join(missing)], "missing"
    return [float(biometrics[key]) for key in FEATURES], [], "valid"


def load_model(path):
    """Load inert JSON, never executable pickle artifacts."""
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    _validate_model(model)
    return model


def _validate_model(model):
    if not isinstance(model, dict) or model.get("format") != "astral-logistic-v1":
        raise ValueError("unsupported model format")
    if model.get("features") != list(FEATURES):
        raise ValueError("model feature order mismatch")
    for key in ("mean", "scale", "weights"):
        values = model.get(key)
        if not isinstance(values, list) or len(values) != len(FEATURES) or not all(map(_number, values)):
            raise ValueError("invalid model " + key)
    if any(value <= 0 for value in model["scale"]):
        raise ValueError("model scales must be positive")
    if not _number(model.get("intercept")):
        raise ValueError("invalid model intercept")
    if not isinstance(model.get("version"), str) or not model["version"]:
        raise ValueError("model version required")
    if not isinstance(model.get("training_data_origin"), str) or model["training_data_origin"] not in {"research", "synthetic"}:
        raise ValueError("model training data origin required")


def build_baseline(events, *, min_windows=5):
    """Robust reference from distinct earlier windows of ONE crew member.

    Caller selects an appropriate rest/calibration period. No labels are inferred.
    The prototype requires >=5 non-overlapping, valid, low-motion windows.
    This minimum is an engineering choice, not a NASA medical threshold.
    """
    if not isinstance(min_windows, int) or isinstance(min_windows, bool) or min_windows < 5:
        raise ValueError("min_windows must be an integer >= 5")
    if len(events) < min_windows:
        raise ValueError("insufficient baseline windows")
    crews = {event.get("crew_id") for event in events}
    origins = {event.get("data_origin") for event in events}
    pipelines = [event.get("feature_pipeline") for event in events]
    if (not all(isinstance(p, str) and p for p in pipelines)
            or len(set(pipelines)) != 1):
        raise ValueError("baseline requires one explicit feature pipeline")
    if len(crews) != 1 or next(iter(crews)) not in {f"AST-{i:02}" for i in range(1, 6)}:
        raise ValueError("baseline requires one valid crew ID")
    if len(origins) != 1 or not origins <= ORIGINS:
        raise ValueError("baseline requires one supported data origin")
    ordered = sorted(events, key=lambda event: _time(event["timestamp"]))
    rows, end_previous, durations = [], None, set()
    for event in ordered:
        start, end = _time(event["window_start"]), _time(event["timestamp"])
        duration = (end - start).total_seconds()
        if not 60 <= duration <= 300 or (end_previous and start < end_previous):
            raise ValueError("baseline windows must be 60..300s and non-overlapping")
        durations.add(duration)
        row, errors, state = _values(event.get("biometrics"))
        if state != "valid" or row[3] > 0.5:
            raise ValueError("baseline requires valid low-motion readings: " + "; ".join(errors))
        rows.append(row)
        end_previous = end
    if len(durations) != 1:
        raise ValueError("baseline requires equal window durations")
    return {
        "crew_id": next(iter(crews)), "data_origin": next(iter(origins)),
        "window_count": len(rows), "end": _iso(end_previous),
        "feature_pipeline": pipelines[0], "window_seconds": durations.pop(),
        "medians": {key: statistics.median(row[i] for row in rows) for i, key in enumerate(FEATURES)},
        "method": "median_of_user_selected_calibration_windows",
    }


def _assess(event, *, model=None, baseline=None, now=None, max_age_seconds=300):
    """Return a JSON-safe result. Omitted now uses real UTC freshness checks.

    Pass an explicit scenario clock for replay; do not relabel replay as live.
    The shared telemetry keys are consumed without modifying the event.
    window_start is a proposed additional input; no fabricated window is inferred.
    """
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    if not _number(max_age_seconds) or max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    result = {
        "schema_version": "wearable-proposal-v1", "source": "wearable",
        "crew_id": event.get("crew_id") if isinstance(event.get("crew_id"), str) else None,
        "timestamp": None, "window_start": None,
        "data_origin": event.get("data_origin") if isinstance(event.get("data_origin"), str) else None,
        "inference_origin": None,
        "feature_pipeline": event.get("feature_pipeline") if isinstance(event.get("feature_pipeline"), str) else None,
        "status": "invalid", "stress_score": None, "confidence": None,
        "score_semantics": None, "model_version": None,
        "quality": {"status": "unknown", "issues": []},
        "observations": [], "baseline": {"status": "unavailable"},
        "context": {}, "limitations": list(LIMITATIONS),
        "evidence_ids": list(SOURCE_IDS), "ai_assisted": True,
    }
    issues = result["quality"]["issues"]
    if result["crew_id"] not in {f"AST-{i:02}" for i in range(1, 6)}:
        issues.append("unsupported crew_id")
    if result["data_origin"] not in ORIGINS:
        issues.append("explicit supported data_origin required")
    try:
        end, start = _time(event.get("timestamp")), _time(event.get("window_start"))
        clock = _time(now) if now is not None else datetime.now(timezone.utc)
        result.update(timestamp=_iso(end), window_start=_iso(start))
        duration = (end - start).total_seconds()
        if not 60 <= duration <= 300:
            issues.append("window duration must be 60..300 seconds")
        if end > clock:
            issues.append("future window")
    except (ValueError, TypeError):
        issues.append("invalid or missing timezone-aware observation window/clock")
    row, errors, state = _values(event.get("biometrics"))
    issues.extend(errors)
    if issues:
        result["status"] = "missing" if state == "missing" and len(issues) == len(errors) else "invalid"
        result["quality"]["status"] = result["status"]
        return result
    if (clock - end).total_seconds() > max_age_seconds:
        result["status"] = result["quality"]["status"] = "stale"
        issues.append("window older than configured freshness limit")
        return result
    result["quality"]["status"] = "usable_summary"
    result["limitations"].append("Summary checks cannot detect all raw-signal artifacts.")
    if row[3] > 0.5:
        result["quality"]["status"] = "motion_caution"
        issues.append("movement may confound physiological interpretation")
    result["observations"] = [{"metric": key, "value": value} for key, value in zip(FEATURES, row)]
    if baseline is not None:
        try:
            if baseline["crew_id"] != event["crew_id"] or baseline["data_origin"] != event["data_origin"]:
                raise ValueError("crew or provenance mismatch")
            if (not isinstance(baseline.get("feature_pipeline"), str)
                    or not baseline["feature_pipeline"]
                    or baseline["feature_pipeline"] != event.get("feature_pipeline")
                    or not _number(baseline.get("window_seconds"))
                    or baseline["window_seconds"] != duration):
                raise ValueError("baseline feature pipeline or duration mismatch")
            if (not isinstance(baseline["window_count"], int) or isinstance(baseline["window_count"], bool)
                    or baseline["window_count"] < 5 or _time(baseline["end"]) > start):
                raise ValueError("insufficient or future baseline")
            medians, errors, state = _values(baseline["medians"])
            if state != "valid":
                raise ValueError("invalid baseline values")
            result["baseline"] = {"status": "available", "window_count": baseline["window_count"],
                                  "end": baseline["end"], "data_origin": baseline["data_origin"],
                                  "feature_pipeline": baseline["feature_pipeline"],
                                  "window_seconds": baseline["window_seconds"]}
            for observation, reference in zip(result["observations"], medians):
                observation.update(baseline_median=reference, delta=round(observation["value"] - reference, 6))
        except (KeyError, ValueError, TypeError):
            result["baseline"] = {"status": "invalid"}
            issues.append("baseline rejected; raw observations retained")
    context = event.get("context", {})
    if isinstance(context, dict):
        for key, high in (("sleep_hours", 24), ("self_report_stress_0_10", 10)):
            value = context.get(key)
            if _number(value) and 0 <= value <= high:
                result["context"][key] = value
            elif value is not None:
                issues.append("ignored invalid context: " + key)
    if result["context"]:
        result["limitations"].append("Sleep/self-report are context only; not inputs to the WESAD model.")
    if model is None:
        result["status"] = "model_unavailable"
        result["limitations"].append("No model supplied; no fabricated stress score.")
        return result
    try:
        _validate_model(model)
        if model.get("training_data_origin") == "research" and (
                not model.get("feature_pipeline") or event.get("feature_pipeline") != model["feature_pipeline"]):
            result["status"] = "incompatible_features"
            issues.append("research model requires the same feature extraction pipeline")
            return result
        if model.get("training_data_origin") == "research" and duration != 60:
            result["status"] = "incompatible_features"
            issues.append("current WESAD research model requires exactly 60 seconds")
            return result
        z = model["intercept"] + sum(w * ((x - m) / s) for x, m, s, w in
                                      zip(row, model["mean"], model["scale"], model["weights"]))
        if not math.isfinite(z):
            raise ValueError("non-finite model output")
        score = 1 / (1 + math.exp(-max(-700, min(700, z))))
    except (ValueError, TypeError, OverflowError):
        result["status"] = "model_invalid"
        issues.append("model rejected")
        return result
    synthetic = model["training_data_origin"] == "synthetic"
    result.update(status="available", stress_score=round(score, 6), model_version=model["version"],
                  inference_origin="simulated_inference" if synthetic else "research_model_inference",
                  score_semantics="synthetic_demo_score" if synthetic else "uncalibrated_WESAD_stress_class_probability")
    result["limitations"].append("Confidence is null: clinical certainty and probability calibration were not established.")
    return result


def assess(event, *, model=None, baseline=None, now=None, max_age_seconds=300):
    """Assess a window and attach offline explanations and design-source links.

    See _assess and CONTRACT_PROPOSAL.md for time, feature and error semantics.
    """
    result = _assess(event, model=model, baseline=baseline, now=now, max_age_seconds=max_age_seconds)
    result["explanation"] = explain(result)
    result["evidence"] = [{"id": key, **REFERENCES[key]} for key in result["evidence_ids"]]
    return result
