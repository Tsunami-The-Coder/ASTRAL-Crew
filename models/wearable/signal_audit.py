"""Check the regression for a previously identified peak-detector limitation; not a physiological simulator.

Requires optional training dependencies. Harmonic waveforms are engineering probes,
not NASA measurements. A rejection is reported separately from accurate extraction.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from .signals import extract_window


def audit():
    rows = []
    time = np.arange(3840) / 64
    for bpm in (60, 90, 120):
        for harmonic in (0, 0.5, 1):
            waveform = (np.sin(2 * np.pi * bpm / 60 * time)
                        + harmonic * np.sin(4 * np.pi * bpm / 60 * time))
            row = {"fundamental_bpm": bpm, "second_harmonic_amplitude": harmonic,
                   "data_origin": "synthetic", "ai_assisted": True}
            try:
                values = extract_window(waveform, np.ones(240) * 2,
                                        np.tile([0, 0, 64], (1920, 1)))
                row.update(status="accepted", extracted=values,
                           pulse_rate_error_bpm=abs(values["heart_rate_bpm"] - bpm))
            except ValueError as exc:
                row.update(status="rejected", reason=str(exc))
            rows.append(row)
    return {"purpose": "Synthetic morphology sensitivity audit; not spaceflight validation",
            "regression_target": "Reject detected secondary-peak double counting; no clinical accuracy claim",
            "probes": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit(), indent=2, allow_nan=False), encoding="utf-8")
    print(f"Wrote signal audit to {args.output}")
