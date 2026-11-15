"""Five-crew synthetic integration examples; no fusion/backend modifications."""
from __future__ import annotations
import argparse
import copy
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .inference import FEATURES, assess, build_baseline, load_model


def fixture_model():
    """Hand-authored fixture coefficients, NOT a trained model or validation."""
    return {"format": "astral-logistic-v1", "version": "synthetic-fixture-v1",
            "features": list(FEATURES), "mean": [70, 50, 2, 0.1], "scale": [20, 20, 3, 0.2],
            "weights": [0.6, -0.8, 0.5, -0.2], "intercept": -1,
            "training_data_origin": "synthetic", "ai_assisted": True}


def event(crew="AST-01", end="2026-11-14T14:30:00Z", **changes):
    clock = datetime.fromisoformat(end.replace("Z", "+00:00"))
    value = {"crew_id": crew, "timestamp": end,
             "window_start": (clock - timedelta(seconds=60)).isoformat().replace("+00:00", "Z"),
             "data_origin": "synthetic", "feature_pipeline": "wrist-bvp-eda-acc-60s-v1",
             "biometrics": dict(zip(FEATURES, [70., 50., 2., 0.1]))}
    value["biometrics"].update(changes)
    return value


def baseline_for(crew):
    return build_baseline([event(crew, f"2026-11-14T14:{minute:02}:00Z") for minute in range(20, 25)])


def scenarios(model=None):
    """Reproducible scenario clock; never claims current live measurements."""
    model = model if model is not None else fixture_model()
    cases = []
    for name in ["nominal", "activity", "crew_change", "missing_sensor", "sensor_disagreement"]:
        events = [event(f"AST-{i:02}") for i in range(1, 6)]
        environment = {"co2_percent": 0.08, "data_origin": "synthetic"}
        expected = "Display individual research indicators; no medical diagnosis."
        voices = []
        if name == "activity":
            events[0]["biometrics"].update(heart_rate_bpm=110., hrv_rmssd_ms=22., motion_level=0.85)
            expected = "Show movement caution; do not label this psychological stress."
        elif name == "crew_change":
            for reading in events[:3]:
                reading["biometrics"].update(heart_rate_bpm=105., hrv_rmssd_ms=18., eda_microsiemens=7.)
            environment["co2_percent"] = 0.32
            expected = "Colin may investigate shared changes and environment; causation is unproven."
        elif name == "missing_sensor":
            events[1]["biometrics"]["eda_microsiemens"] = None
            expected = "AST-02 is missing, with null score; never replace it with normal."
        elif name == "sensor_disagreement":
            events[0]["biometrics"].update(heart_rate_bpm=105., hrv_rmssd_ms=18., eda_microsiemens=7.)
            voices = [{"crew_id": "AST-01", "stress_score": 0.1, "source": "voice", "data_origin": "synthetic",
                       "timestamp": events[0]["timestamp"], "window_start": events[0]["window_start"],
                       "note": "Mock only; not Ben's actual schema/model."}]
            expected = "Flag disagreement; no averaging of uncalibrated model scores."
        events[0]["context"] = {"sleep_hours": 5.5, "self_report_stress_0_10": 4}
        cases.append({"scenario": name, "data_origin": "synthetic", "ai_assisted": True,
                      "clock": "2026-11-14T14:30:00Z", "inputs": events, "environment": environment,
                      "voice_mocks": voices, "integration_expectation": expected,
                      "wearable_results": [assess(reading, model=model, baseline=baseline_for(reading["crew_id"]),
                                                  now="2026-11-14T14:30:00Z") for reading in events]})
    return cases


def report_html(cases):
    sections = []
    for case in cases:
        rows = []
        explanations = []
        for result in case["wearable_results"]:
            score = "Unavailable" if result["stress_score"] is None else f'{result["stress_score"]:.3f}'
            rows.append("<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in (
                result["crew_id"], result["status"], score, result["quality"]["status"], result["inference_origin"])) + "</tr>")
            explanations.append('<details><summary>' + html.escape(result["crew_id"]) + ' - explanation</summary><ul>'
                                + ''.join('<li>' + html.escape(line) + '</li>' for line in result["explanation"]) + '</ul></details>')
        sections.append(f'<section><h2>{html.escape(case["scenario"].replace("_", " ").title())}</h2>'
                        f'<p>{html.escape(case["integration_expectation"])}</p><table><thead><tr>'
                        '<th>Crew</th><th>Availability</th><th>Indicator</th><th>Quality</th><th>Inference</th>'
                        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table>' + ''.join(explanations) + '</section>')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASTRAL-Crew | Wearable verification</title><style>
body{font:16px system-ui;margin:40px auto;max-width:1100px;padding:0 24px;background:#0c1523;color:#e7eef6}
h1{font-size:36px}h2{font-size:24px}p{line-height:1.6;color:#b8c9dd}section{margin:26px 0;padding:24px;background:#14243a;border-radius:12px}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px 8px;border-bottom:1px solid #30445e}
strong{color:#ffd479}a{color:#8acfff}details{margin-top:14px;line-height:1.6}summary{cursor:pointer}</style><h1>ASTRAL-Crew / Wearable</h1>
<p><strong>ALL SCENARIOS ARE SYNTHETIC. AI-assisted code and demo data.</strong><br>
Engineering demonstration; not clinical validation. No real crew records. No live spacecraft controls.</p>''' + "".join(sections) + '''
<section><h2>Evidence and limits</h2><p>NASA research motivates monitoring physiology, activity and sleep.
It does not validate these scores or supply our numerical thresholds. See SOURCES.md and MODEL_CARD.md.</p>
<p><a href="https://humanresearchroadmap.nasa.gov/Tasks/task.aspx?i=1160">NASA stress research</a> ·
<a href="https://www.nasa.gov/reference/archer/">ARCHeR</a> ·
<a href="https://www.nasa.gov/reference/standard-measures/">Standard Measures</a></p></section></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, help="Optional locally trained JSON model; data remain synthetic")
    args = parser.parse_args()
    model = load_model(args.model) if args.model else None
    cases = scenarios(model)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "wearable-demo.json").write_text(json.dumps(cases, indent=2, allow_nan=False), encoding="utf-8")
    (args.output / "wearable-demo.html").write_text(report_html(cases), encoding="utf-8")
    total = sum(len(case["wearable_results"]) for case in cases)
    print(f"Wrote {len(cases)} synthetic scenarios / {total} crew results to {args.output}")


if __name__ == "__main__":
    main()
