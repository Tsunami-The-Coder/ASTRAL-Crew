"""Wrist feature extraction. Optional numpy/scipy dependencies; AI-assisted.

This is a simple research baseline, not a validated PPG artifact detector.
Pulse interval RMSSD is a proxy and is not ECG-derived HRV.
"""
from __future__ import annotations
import numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks, correlate

FEATURE_PIPELINE = "wrist-bvp-eda-acc-60s-v1"
SAMPLE_RATES = {"BVP": 64, "EDA": 4, "ACC": 32}


def extract_window(bvp, eda, acc):
    """Accept exactly 60s of synchronized WESAD wrist signals.

    ACC input uses original E4 units (1/64 g). motion_level is our proposed
    unitless mapping: min(RMS acceleration about per-axis mean / 0.2 g, 1).
    0.2 g and quality bounds are engineering choices, not NASA thresholds.
    """
    bvp = np.asarray(bvp, dtype=float).reshape(-1)
    eda = np.asarray(eda, dtype=float).reshape(-1)
    acc = np.asarray(acc, dtype=float)
    if bvp.shape != (3840,) or eda.shape != (240,) or acc.shape != (1920, 3):
        raise ValueError("requires 60 seconds: BVP[3840], EDA[240], ACC[1920,3]")
    if not all(np.isfinite(values).all() for values in (bvp, eda, acc)):
        raise ValueError("non-finite signal")
    if np.std(bvp) < 1e-8 or np.any(eda < 0) or np.any(eda > 100):
        raise ValueError("flat BVP or invalid EDA")
    filtered = sosfiltfilt(butter(3, [0.5, 4.0], fs=64, btype="bandpass", output="sos"), bvp)
    peaks, _ = find_peaks(filtered, distance=16, prominence=max(0.25 * np.std(filtered), 1e-8))
    if len(peaks) < 25 or len(peaks) > 200:
        raise ValueError("insufficient or implausible pulse peaks")
    intervals = np.diff(peaks) / 64 * 1000
    valid = (intervals >= 300) & (intervals <= 2000)
    # Only consecutive valid intervals; never bridge deleted artifacts.
    consecutive = valid[1:] & valid[:-1]
    if valid.mean() < 0.9 or consecutive.sum() < 20:
        raise ValueError("too many implausible pulse intervals")
    hr = 60000 / np.mean(intervals[valid])
    # Independent periodicity check catches secondary peaks counted as beats.
    # Conservative engineering gate, not validated medical signal quality.
    centered_pulse = filtered - filtered.mean()
    ac = correlate(centered_pulse, centered_pulse, mode="full", method="fft")[len(filtered)-1:]
    candidates, _ = find_peaks(ac)
    candidates = candidates[(candidates >= 20) & (candidates <= 128)]
    if not len(candidates) or ac[0] <= 0:
        raise ValueError("ambiguous pulse periodicity")
    lag = candidates[np.argmax(ac[candidates])]
    periodic_hr = 60 * 64 / lag
    if ac[lag] / ac[0] < 0.3 or abs(hr - periodic_hr) / periodic_hr > 0.20:
        raise ValueError("pulse peaks disagree with waveform periodicity")
    rmssd = np.sqrt(np.mean(np.diff(intervals)[consecutive] ** 2))
    if not 20 <= hr <= 240 or not 0 <= rmssd <= 500:
        raise ValueError("derived pulse features outside engineering bounds")
    acceleration_g = acc / 64.0
    centered = acceleration_g - acceleration_g.mean(axis=0)
    motion = min(float(np.sqrt(np.mean(np.sum(centered ** 2, axis=1)))) / 0.2, 1.0)
    return {"heart_rate_bpm": float(hr), "hrv_rmssd_ms": float(rmssd),
            "eda_microsiemens": float(eda.mean()), "motion_level": motion}
