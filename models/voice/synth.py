"""SYNTHETIC speech-like audio and cabin noise, for tests and demos only.

Nothing here is real speech. It is a source-filter vowel model:
glottal pulse train (with pitch, jitter, shimmer) -> formant resonators ->
syllable-rate amplitude envelope. The "aroused" variant applies the
directions reported in the stressed-speech literature (higher and more
variable pitch, more vocal effort / high-frequency energy, more jitter).
Magnitudes are team assumptions, chosen only so tests have something to
detect. Every output of this module must be labelled data_type="synthetic".

Cabin noise: fan hum (fundamental + harmonics, 50-200 Hz) plus pink noise,
mixed at a requested SNR, so the band-pass filter can be tested.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import lfilter

from .features import SR

VOWEL_FORMANTS = [(700, 1220, 2600), (300, 870, 2240), (530, 1840, 2480), (570, 840, 2410), (440, 1020, 2240)]


@dataclass(frozen=True)
class VoiceProfile:
    """A synthetic speaker. f0 in Hz, tilt = spectral-tilt pole (higher = darker)."""
    f0_hz: float = 120.0
    f0_var: float = 0.06
    jitter: float = 0.005
    shimmer: float = 0.04
    tilt: float = 0.92
    level: float = 0.25


SPEAKERS = {
    "AST-01": VoiceProfile(f0_hz=115, tilt=0.93),
    "AST-02": VoiceProfile(f0_hz=205, f0_var=0.07, tilt=0.91),
    "AST-03": VoiceProfile(f0_hz=130, tilt=0.92, level=0.22),
    "AST-04": VoiceProfile(f0_hz=190, f0_var=0.05, tilt=0.90),
    "AST-05": VoiceProfile(f0_hz=160, f0_var=0.06, tilt=0.92),
}


def aroused(p: VoiceProfile, amount: float = 1.0) -> VoiceProfile:
    """Literature directions for high-arousal speech, scaled by `amount` (0-1)."""
    return VoiceProfile(
        f0_hz=p.f0_hz * (1 + 0.28 * amount),
        f0_var=p.f0_var * (1 + 1.2 * amount),
        jitter=p.jitter * (1 + 1.5 * amount),
        shimmer=p.shimmer * (1 + 0.8 * amount),
        tilt=p.tilt - 0.17 * amount,       # flatter tilt = more high-frequency energy
        level=p.level * (1 + 0.8 * amount),  # ~ +5 dB vocal effort
    )


def _resonator(x: np.ndarray, f: float, bw: float, sr: int) -> np.ndarray:
    r = np.exp(-np.pi * bw / sr)
    a = [1, -2 * r * np.cos(2 * np.pi * f / sr), r * r]
    return lfilter([1 - r], a, x)


def utterance(profile: VoiceProfile, seconds: float = 3.0, seed: int = 0, sr: int = SR) -> np.ndarray:
    """One synthetic 'sentence' of ~4 syllables/s with short pauses."""
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    out = np.zeros(n)
    t = 0
    syl = 0
    while t < n:
        dur = int(rng.uniform(0.15, 0.28) * sr)
        if t + dur > n:
            break
        if syl % 5 == 4:  # pause every 5th slot
            t += int(0.12 * sr)
            syl += 1
            continue
        # glottal pulses with intonation, jitter and shimmer
        f0_syl = profile.f0_hz * (1 + profile.f0_var * rng.standard_normal())
        src = np.zeros(dur)
        pos = 0.0
        while pos < dur:
            period = sr / max(60.0, f0_syl * (1 + profile.jitter * rng.standard_normal()))
            amp = 1 + profile.shimmer * rng.standard_normal()
            src[int(pos)] = amp
            pos += period
        src = lfilter([1], [1, -profile.tilt], src)  # glottal spectral tilt
        f1, f2, f3 = VOWEL_FORMANTS[rng.integers(len(VOWEL_FORMANTS))]
        v = sum(_resonator(src, f, bw, sr) for f, bw in ((f1, 80), (f2, 100), (f3, 140)))
        env = np.sin(np.linspace(0, np.pi, dur)) ** 0.6
        out[t:t + dur] += v * env
        t += dur + int(rng.uniform(0.02, 0.06) * sr)
        syl += 1
    out = out / (np.max(np.abs(out)) + 1e-9) * profile.level
    out += rng.normal(0, 1e-4, n)  # mic self-noise
    return out.astype(np.float32)


def pink_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    white = rng.standard_normal(n)
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    p = lfilter(b, a, white)
    return p / (np.std(p) + 1e-12)


def cabin_noise(n: int, seed: int = 0, hum_hz: float = 60.0, sr: int = SR) -> np.ndarray:
    """Fan-like hum (harmonics up to ~200 Hz) dominating, plus broadband pink noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / sr
    hum = sum((1 / k) * np.sin(2 * np.pi * hum_hz * k * t + rng.uniform(0, 2 * np.pi)) for k in range(1, 4))
    hum = hum / (np.std(hum) + 1e-12)
    return (0.85 * hum + 0.35 * pink_noise(n, rng)).astype(np.float32)


def mix_at_snr(speech: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    ps = np.mean(speech ** 2)
    pn = np.mean(noise ** 2) + 1e-12
    scale = np.sqrt(ps / (pn * 10 ** (snr_db / 10)))
    y = speech + scale * noise[: len(speech)]
    peak = np.max(np.abs(y))
    return (y / peak * 0.9 if peak > 0.99 else y).astype(np.float32)

