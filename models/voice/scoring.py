"""Turn baseline deviations into a 0-1 voice stress indicator, a confidence and
an explanation.

stress_score is a RESEARCH INDICATOR of vocal arousal relative to the
astronaut's own calm baseline. It is not a clinical score or a diagnosis.

Two parts:
1. Rule score (always available): signed, weighted mean of baseline z-scores
   for features whose direction under stress/arousal is reported in the
   literature, mapped through a logistic curve. Weights and the mapping are
   team assumptions (documented in MODEL_CARD.md), not fitted values.
2. Optional learned score: if models/voice/model.json exists (trained by
   train.py on RAVDESS with per-actor baselines), its probability is averaged
   with the rule score. No model is shipped until it has actually been trained.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .features import FEATURE_NAMES, AudioQuality

# direction (+ = rises with arousal, - = falls) and relative weight
AROUSAL_WEIGHTS: dict[str, float] = {
    "f0_mean_hz": +1.0,          # pitch rises under stress (Hansen & Patil 2007)
    "f0_std_hz": +0.5,           # more pitch variability
    "f0_range_hz": +0.5,
    "energy_db_mean": +0.6,      # louder / more vocal effort (lower weight: mic distance also changes it)
    "hf_ratio": +0.9,            # flatter spectral tilt = more high-frequency energy
    "spectral_centroid_hz": +0.5,
    "jitter_proxy": +0.4,
    "shimmer_proxy_db": +0.3,
    "teo_autoenv_mean": -0.8,    # TEO autocorrelation envelope falls with stress (Zhou et al. 2001)
}
LOGISTIC_SLOPE = 1.6
LOGISTIC_CENTER = 1.0   # 1 SD of weighted arousal deviation -> score 0.5
MFCC_KEYS = [k for k in FEATURE_NAMES if k.startswith("mfcc_")]
PROFILE_MISMATCH_Z = 3.0

READABLE = {
    "f0_mean_hz": "pitch", "f0_std_hz": "pitch variability", "f0_range_hz": "pitch range",
    "energy_db_mean": "loudness", "hf_ratio": "vocal effort (high-frequency energy)",
    "spectral_centroid_hz": "voice brightness", "jitter_proxy": "pitch instability",
    "shimmer_proxy_db": "loudness instability", "teo_autoenv_mean": "airflow regularity (TEO)",
}

MODEL_PATH = Path(__file__).resolve().parent / "model.json"


def weighted_deviation(z: dict[str, float]) -> float:
    tot = sum(abs(w) for w in AROUSAL_WEIGHTS.values())
    return sum(w * z[k] for k, w in AROUSAL_WEIGHTS.items()) / tot


def rule_score(z: dict[str, float]) -> float:
    d = weighted_deviation(z)
    return 1.0 / (1.0 + math.exp(-LOGISTIC_SLOPE * (d - LOGISTIC_CENTER)))


def profile_distance(z: dict[str, float]) -> float:
    """Mean |z| of MFCCs: how different the voice timbre is from the baseline.
    Very large values suggest a different speaker, a different microphone or
    a mislabelled crew_id, not stress."""
    return float(np.mean([abs(z[k]) for k in MFCC_KEYS]))


def top_contributors(z: dict[str, float], k: int = 3) -> list[dict]:
    items = [(name, w * z[name]) for name, w in AROUSAL_WEIGHTS.items()]
    items.sort(key=lambda t: -abs(t[1]))
    return [{"feature": n, "label": READABLE[n], "z": round(z[n], 2), "contribution": round(c, 2)}
            for n, c in items[:k]]


def explanation(z: dict[str, float], score: float) -> str:
    parts = []
    for c in top_contributors(z, 3):
        if abs(c["z"]) >= 1.0:
            arrow = "above" if c["z"] > 0 else "below"
            parts.append(f"{c['label']} {abs(c['z']):.1f} SD {arrow} own baseline")
    level = "elevated above" if score >= 0.6 else "mildly above" if score >= 0.4 else "close to"
    lead = f"Vocal arousal {level} personal baseline"
    tail = " (" + "; ".join(parts) + ")" if parts else ""
    return lead + tail + ". Research indicator, not a diagnosis."


def confidence(q: AudioQuality, baseline_n: int, mismatch: float, model_used: bool) -> tuple[float, list[str]]:
    """Heuristic confidence in [0.05, 0.95] plus quality flags.
    NOT a calibrated probability; it tells fusion how much to trust this record."""
    flags = []
    c = 0.85
    c *= min(1.0, q.speech_s / 3.0) ** 0.5
    if q.speech_s < 1.5:
        flags.append("short_utterance")
    if q.snr_db < 5:
        c *= 0.5
        flags.append("low_snr")
    elif q.snr_db < 12:
        c *= 0.75
        flags.append("moderate_noise")
    if q.clipped:
        c *= 0.7
        flags.append("clipping")
    c *= min(1.0, baseline_n / 10.0) ** 0.5
    if baseline_n < 10:
        flags.append("small_baseline")
    if mismatch > PROFILE_MISMATCH_Z:
        c *= 0.5
        flags.append("voice_profile_mismatch")
    if model_used:
        c = min(0.95, c * 1.05)
    return float(np.clip(round(c, 3), 0.05, 0.95)), flags


# ------------------------------------------------------------- optional model
_MODEL_CACHE: dict[str, dict] = {}


def load_model(path: Path | None = MODEL_PATH) -> dict | None:
    if path is None or not Path(path).exists():
        return None
    key = str(path)
    if key not in _MODEL_CACHE:
        m = json.loads(Path(path).read_text(encoding="utf-8"))
        if m.get("feature_names") != FEATURE_NAMES:
            raise ValueError(f"{path} was trained on a different feature set; retrain with train.py")
        _MODEL_CACHE[key] = m
    return _MODEL_CACHE[key]


def model_score(model: dict, z: dict[str, float]) -> float:
    x = np.array([z[k] for k in FEATURE_NAMES])
    x = (x - np.array(model["scaler_mean"])) / np.array(model["scaler_scale"])
    logit = float(np.dot(model["coef"], x) + model["intercept"])
    return 1.0 / (1.0 + math.exp(-logit))
