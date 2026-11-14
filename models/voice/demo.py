"""End-to-end SYNTHETIC demo: run the real voice pipeline on Eleni's scenarios.

Eleni's scenarios (data/scenarios/<name>/voice_events.csv) contain the voice
stress level each astronaut is ASSUMED to have at each moment. Until now,
fusion used those numbers directly as mock outputs. This script replaces the
mock with the actual pipeline:

    assumed voice level  ->  synthesize a speech-like utterance with that much
    arousal, mixed with cabin fan noise  ->  band-pass, features, personal
    baseline, score  ->  contract record (source="voice", data_type="synthetic")

Output per scenario: data/processed/voice_outputs/<scenario>.jsonl (contract
records only, drop-in for Colin) and <scenario>.details.jsonl.

What this shows: the code path works end to end, on all scenarios, with noise,
and its scores track the intended arousal. What it does NOT show: accuracy on
real human stress (the audio is synthetic). Say so on any slide.

    python -m models.voice.demo                      # 09_demo_storyline
    python -m models.voice.demo --all --snr 15
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import synth
from .inference import VoiceStressEstimator, write_jsonl

SCEN_ROOT = Path("data/scenarios")
OUT_ROOT = Path("data/processed/voice_outputs")
CALM_LEVEL = 0.18   # scenario generator's calm voice level (team_assumption)
FULL_DELTA = 0.55   # scenario generator's voice_delta for full stress (team_assumption)


def arousal_amount(level: float) -> float:
    return float(np.clip((level - CALM_LEVEL) / FULL_DELTA, 0.0, 1.0))


def build_estimator(snr_db: float, seed: int = 0) -> VoiceStressEstimator:
    est = VoiceStressEstimator(baseline_path=None, model_path=None)
    for i, (crew, prof) in enumerate(synth.SPEAKERS.items()):
        clips = []
        for s in range(8):
            u = synth.utterance(prof, 3.0, seed=1000 * (i + 1) + s + seed)
            clips.append(synth.mix_at_snr(u, synth.cabin_noise(len(u), seed=s + 50 * i), snr_db))
        est.enroll(crew, clips, data_type="synthetic")
    return est


def run_scenario(name: str, snr_db: float = 15.0, seed: int = 0, out_root: Path = OUT_ROOT,
                 limit: int | None = None) -> dict:
    ve = pd.read_csv(SCEN_ROOT / name / "voice_events.csv")
    if limit:
        ve = ve.head(limit)
    est = build_estimator(snr_db, seed)
    records, details, pairs = [], [], []
    for j, r in enumerate(ve.itertuples(index=False)):
        prof = synth.aroused(synth.SPEAKERS[r.crew_id], arousal_amount(r.voice_stress_score))
        u = synth.utterance(prof, 3.0, seed=10_000 + j + seed)
        u = synth.mix_at_snr(u, synth.cabin_noise(len(u), seed=j + seed), snr_db)
        res = est.analyze(u, r.crew_id, r.timestamp, data_type="synthetic")
        details.append({"scenario_voice_level": r.voice_stress_score, **res.details})
        if res.ok:
            records.append(res.record)
            pairs.append((r.voice_stress_score, res.record["stress_score"]))
    out_root.mkdir(parents=True, exist_ok=True)
    n = write_jsonl(records, out_root / f"{name}.jsonl")
    with open(out_root / f"{name}.details.jsonl", "w", encoding="utf-8") as f:
        for d in details:
            f.write(json.dumps(d, default=float) + "\n")
    a = np.array(pairs)
    corr = float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]) if len(a) > 2 and a[:, 0].std() > 0 else float("nan")
    return {"scenario": name, "utterances": int(len(ve)), "records": n,
            "pearson_r_vs_intended": round(corr, 3), "snr_db": snr_db,
            "mean_score_calm": round(float(a[a[:, 0] < 0.3, 1].mean()), 3) if (a[:, 0] < 0.3).any() else None,
            "mean_score_stressed": round(float(a[a[:, 0] >= 0.5, 1].mean()), 3) if (a[:, 0] >= 0.5).any() else None,
            "data_type": "synthetic"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="09_demo_storyline")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--snr", type=float, default=15.0, help="speech-to-cabin-noise ratio in dB")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    names = sorted(p.name for p in SCEN_ROOT.iterdir() if p.is_dir()) if a.all else [a.scenario]
    summary = []
    for n in names:
        s = run_scenario(n, a.snr, a.seed)
        summary.append(s)
        print(f"{n:<28} {s['records']:>4} records  r={s['pearson_r_vs_intended']:.3f}  "
              f"calm={s['mean_score_calm']}  stressed={s['mean_score_stressed']}")
    (OUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nRecords -> {OUT_ROOT}/<scenario>.jsonl   (SYNTHETIC audio; tests the pipeline, not real stress)")


if __name__ == "__main__":
    main()
