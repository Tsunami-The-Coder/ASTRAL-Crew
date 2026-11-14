"""Cabin-noise robustness check (VALIDATION_PLAN.md, Tier 3 "if time allows").

Measurable without labelled spaceflight audio: inject fan-like hum + pink
noise into SYNTHETIC speech at several SNRs and compare three pipelines:
no filter / 300-3400 Hz Butterworth band-pass / band-pass + spectral
subtraction of the noise measured in speech pauses (the default).

Metrics per condition (N utterances each, 4 synthetic speakers):
  * false_alarm_rate: calm speech scored >= 0.6
  * detection_rate:   fully aroused speech scored >= 0.6
  * feature_drift_sd: mean |z| of the arousal features of calm speech
                      relative to the speaker's baseline (0 = no drift)

Baselines are enrolled at 20 dB SNR (normal cabin), then tested at each SNR.
Results: models/voice/results/robustness.json. Synthetic signals: this tests
the filter, the noise subtraction and the scoring logic, not human physiology.

    python -m models.voice.robustness            # ~1 min
    python -m models.voice.robustness --n 10     # quick
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import scoring, synth
from .baseline import BaselineStore
from .features import extract

HERE = Path(__file__).resolve().parent
SNRS = [30, 20, 10, 5, 0]
ENROLL_SNR = 20


def _noisy(prof, seed, snr):
    u = synth.utterance(prof, 3.0, seed=seed)
    return synth.mix_at_snr(u, synth.cabin_noise(len(u), seed=seed + 7), snr)


def run(n: int = 25, snrs=SNRS) -> dict:
    out = {"enroll_snr_db": ENROLL_SNR, "n_per_condition": n * len(synth.SPEAKERS), "data_type": "synthetic",
           "conditions": []}
    configs = [("no_filter", False, False), ("bandpass", True, False), ("bandpass+denoise", True, True)]
    for label, use_filter, dn in configs:
        store = BaselineStore(None)
        for i, (crew, prof) in enumerate(synth.SPEAKERS.items()):
            b = store.get_or_create(crew, "synthetic")
            for s in range(10):
                b.add(extract(_noisy(prof, 500 + 100 * i + s, ENROLL_SNR), apply_filter=use_filter, denoise=dn))
        for snr in snrs:
            calm, hot, drift = [], [], []
            for i, (crew, prof) in enumerate(synth.SPEAKERS.items()):
                b = store.get(crew)
                for s in range(n):
                    zc = b.z(extract(_noisy(prof, 9000 + 100 * i + s, snr), apply_filter=use_filter, denoise=dn))
                    zh = b.z(extract(_noisy(synth.aroused(prof, 1.0), 7000 + 100 * i + s, snr), apply_filter=use_filter, denoise=dn))
                    calm.append(scoring.rule_score(zc))
                    hot.append(scoring.rule_score(zh))
                    drift.append(np.mean([abs(zc[k]) for k in scoring.AROUSAL_WEIGHTS]))
            row = {"pipeline": label, "snr_db": snr,
                   "false_alarm_rate": round(float(np.mean(np.array(calm) >= 0.6)), 3),
                   "detection_rate": round(float(np.mean(np.array(hot) >= 0.6)), 3),
                   "mean_score_calm": round(float(np.mean(calm)), 3),
                   "mean_score_aroused": round(float(np.mean(hot)), 3),
                   "feature_drift_sd": round(float(np.mean(drift)), 3)}
            out["conditions"].append(row)
            print(row)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25, help="utterances per speaker per condition")
    ap.add_argument("--out", type=Path, default=HERE / "results" / "robustness.json")
    a = ap.parse_args()
    res = run(a.n)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
