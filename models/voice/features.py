"""Acoustic feature extraction for ASTRAL-Crew voice stress estimation.

Pure numpy/scipy (no librosa), so it runs offline on any onboard computer and
adds no new dependency to the team environment.

Pipeline for one utterance:
    raw audio -> mono float, 16 kHz
              -> 4th-order Butterworth band-pass 300-3400 Hz (removes cabin fan hum
                 and high-frequency hiss; the classic telephone speech band)
              -> 25 ms frames, 10 ms hop
              -> energy-based voice activity detection (VAD)
              -> noise spectrum from the pauses, spectral subtraction
              -> per-frame MFCC, F0 (autocorrelation), Teager energy (TEO),
                 spectral centroid, high-frequency energy ratio
              -> utterance-level summary vector (FEATURE_NAMES)

Scientific basis (see SOURCES.md):
  * TEO features for stressed speech: Cairns & Hansen 1994; Zhou, Hansen &
    Kaiser 2001 (TEO-CB-Auto-Env). We implement a simplified version.
  * Pitch, energy and spectral-tilt changes under stress/arousal:
    Hansen & Patil 2007; Giddens et al. 2013 (review).
  * MFCCs: Davis & Mermelstein 1980.

Every feature here is a measurement, not a diagnosis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import gcd
from pathlib import Path

import numpy as np
from scipy.fft import dct, rfft
from scipy.io import wavfile
from scipy.signal import butter, resample_poly, sosfiltfilt

SR = 16000
FRAME_S = 0.025
HOP_S = 0.010
BAND_HZ = (300.0, 3400.0)
F0_RANGE_HZ = (75.0, 400.0)
N_MFCC = 13
N_MELS = 26
TEO_BANDS_HZ = [(300, 600), (600, 1000), (1000, 1500), (1500, 2200), (2200, 3400)]
EPS = 1e-10

# Utterance-level features, in a fixed order. Units in the names where they exist.
FEATURE_NAMES: list[str] = (
    ["f0_mean_hz", "f0_std_hz", "f0_range_hz", "jitter_proxy",
     "energy_db_mean", "energy_db_std", "shimmer_proxy_db",
     "spectral_centroid_hz", "hf_ratio",
     "teo_log_mean", "teo_autoenv_mean", "voiced_frac"]
    + [f"mfcc_{i}_mean" for i in range(1, N_MFCC)]
)


@dataclass
class AudioQuality:
    """Signal-quality facts used for confidence and for honest reporting."""
    duration_s: float
    speech_s: float
    voiced_frac: float
    snr_db: float
    low_freq_hum_ratio: float
    clipped: bool

    def as_dict(self) -> dict:
        return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


@dataclass
class UtteranceFeatures:
    values: dict[str, float]
    quality: AudioQuality
    frames: dict[str, np.ndarray] = field(default_factory=dict, repr=False)

    def vector(self) -> np.ndarray:
        return np.array([self.values[k] for k in FEATURE_NAMES], dtype=float)


# --------------------------------------------------------------------------- I/O
def to_mono_float(x: np.ndarray) -> np.ndarray:
    if np.issubdtype(x.dtype, np.integer):
        x = x.astype(np.float32) / float(np.iinfo(x.dtype).max)
    x = np.asarray(x, dtype=np.float32)
    return x.mean(axis=1) if x.ndim == 2 else x


def resample(x: np.ndarray, sr: int, target_sr: int = SR) -> np.ndarray:
    if sr == target_sr:
        return x.astype(np.float32)
    g = gcd(int(sr), int(target_sr))
    return resample_poly(x, target_sr // g, int(sr) // g).astype(np.float32)


def load_wav(path: str | Path, target_sr: int = SR) -> np.ndarray:
    """Read a WAV file and return mono float32 at 16 kHz.

    MP3 (e.g. NASA Artemis audio) must be converted first:
        ffmpeg -i clip.mp3 -ac 1 -ar 16000 clip.wav
    """
    sr, x = wavfile.read(str(path))
    return resample(to_mono_float(x), sr, target_sr)


# ------------------------------------------------------------------- filtering
def bandpass(x: np.ndarray, sr: int = SR, band: tuple[float, float] = BAND_HZ, order: int = 4) -> np.ndarray:
    """Zero-phase 4th-order Butterworth band-pass (default 300-3400 Hz)."""
    hi = min(band[1], 0.45 * sr)
    sos = butter(order, [band[0], hi], btype="bandpass", fs=sr, output="sos")
    if len(x) < 64:
        return x.astype(np.float32)
    return sosfiltfilt(sos, x).astype(np.float32)


def frame_signal(x: np.ndarray, sr: int = SR, frame_s: float = FRAME_S, hop_s: float = HOP_S) -> np.ndarray:
    n, h = int(round(frame_s * sr)), int(round(hop_s * sr))
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    count = 1 + (len(x) - n) // h
    idx = np.arange(n)[None, :] + h * np.arange(count)[:, None]
    return x[idx]


def frame_db(frames: np.ndarray) -> np.ndarray:
    return 20 * np.log10(np.sqrt(np.mean(frames ** 2, axis=1)) + EPS)


def vad_mask(db: np.ndarray, rel_floor_db: float = 30.0, over_noise_db: float = 8.0) -> np.ndarray:
    """Energy VAD: a frame is speech if it is well above the noise floor and
    not more than `rel_floor_db` below the loudest frame."""
    if db.size == 0:
        return np.zeros(0, dtype=bool)
    noise = np.percentile(db, 10)
    thr = max(noise + over_noise_db, db.max() - rel_floor_db)
    mask = db > thr
    # close 1-2 frame gaps so syllables are not chopped up
    for _ in range(2):
        m = mask.copy()
        m[1:-1] |= mask[:-2] & mask[2:]
        mask = m
    return mask


# ------------------------------------------------------------------- spectral
def mel_filterbank(n_fft: int, sr: int = SR, n_mels: int = N_MELS,
                   fmin: float = BAND_HZ[0], fmax: float = BAND_HZ[1]) -> np.ndarray:
    def hz2mel(f):
        return 2595 * np.log10(1 + f / 700)

    def mel2hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    mels = np.linspace(hz2mel(fmin), hz2mel(fmax), n_mels + 2)
    bins = np.floor((n_fft + 1) * mel2hz(mels) / sr).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        l, c, r = bins[m - 1], bins[m], bins[m + 1]
        if c > l:
            fb[m - 1, l:c] = (np.arange(l, c) - l) / (c - l)
        if r > c:
            fb[m - 1, c:r] = (r - np.arange(c, r)) / (r - c)
    return fb


def power_spectrum(frames: np.ndarray, n_fft: int = 512, noise_psd: np.ndarray | None = None) -> np.ndarray:
    """Power spectrum per frame. If `noise_psd` is given (mean spectrum of the
    non-speech frames), it is subtracted with a spectral floor (classic
    spectral subtraction, Boll 1979), so steady cabin noise does not make the
    voice look brighter or louder than it is."""
    win = np.hamming(frames.shape[1])
    p = (np.abs(rfft(frames * win, n=n_fft, axis=1)) ** 2) / n_fft
    if noise_psd is not None:
        p = np.maximum(p - noise_psd[None, :], 0.05 * p)
    return p


def noise_spectrum(frames: np.ndarray, mask: np.ndarray, n_fft: int = 512, min_frames: int = 5) -> np.ndarray | None:
    """Mean power spectrum of non-speech frames, or None if there are too few pauses."""
    quiet = frames[~mask[: len(frames)]]
    if len(quiet) < min_frames:
        return None
    return power_spectrum(quiet, n_fft).mean(axis=0)


def mfcc(frames: np.ndarray, sr: int = SR, n_mfcc: int = N_MFCC, n_fft: int = 512,
         noise_psd: np.ndarray | None = None) -> np.ndarray:
    """MFCCs. Note: pre-emphasis is applied AFTER spectral subtraction (as a
    spectral weight) so the same noise estimate can be used."""
    pspec = power_spectrum(frames, n_fft, noise_psd)
    w = np.abs(1 - 0.97 * np.exp(-2j * np.pi * np.fft.rfftfreq(n_fft, 1 / sr) / sr)) ** 2
    pspec = pspec * w[None, :]
    mel = np.maximum(pspec @ mel_filterbank(n_fft, sr).T, EPS)
    return dct(np.log(mel), type=2, axis=1, norm="ortho")[:, :n_mfcc]


def spectral_stats(frames: np.ndarray, sr: int = SR, n_fft: int = 512,
                   noise_psd: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Spectral centroid (Hz) and ratio of energy above 1 kHz (vocal effort cue)."""
    p = power_spectrum(frames, n_fft, noise_psd)
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    total = p.sum(axis=1) + EPS
    centroid = (p * freqs).sum(axis=1) / total
    hf = p[:, freqs >= 1000].sum(axis=1) / total
    return centroid, hf


# ---------------------------------------------------------------------- pitch
def f0_autocorr(frames: np.ndarray, sr: int = SR, f_range: tuple[float, float] = F0_RANGE_HZ,
                voicing_thr: float = 0.45) -> np.ndarray:
    """Per-frame F0 (Hz) by normalised autocorrelation; 0 = unvoiced.

    Runs on band-passed audio. The fundamental itself may be attenuated below
    300 Hz, but its period is still present in the harmonics, so the
    autocorrelation peak still lands on the true pitch period."""
    lo, hi = int(sr / f_range[1]), int(sr / f_range[0])
    out = np.zeros(len(frames))
    for i, fr in enumerate(frames):
        fr = fr - fr.mean()
        e = np.dot(fr, fr)
        if e < EPS or hi >= len(fr):
            continue
        ac = np.correlate(fr, fr, mode="full")[len(fr) - 1:]
        # unbiased normalisation so long lags are not penalised
        ac = ac / (e * (len(fr) - np.arange(len(fr))) / len(fr))
        seg = ac[lo:hi + 1]
        k = int(np.argmax(seg))
        if seg[k] < voicing_thr:
            continue
        lag = lo + k
        # parabolic interpolation for sub-sample precision
        if 0 < k < len(seg) - 1:
            a, b, c = seg[k - 1], seg[k], seg[k + 1]
            d = a - 2 * b + c
            if abs(d) > EPS:
                lag = lag + 0.5 * (a - c) / d
        out[i] = sr / lag
    return out


def pitch_frames(x: np.ndarray, sr: int = SR) -> np.ndarray:
    """F0 needs >= 2 pitch periods, so use 40 ms windows on the same 10 ms hop."""
    return f0_autocorr(frame_signal(x, sr, frame_s=0.040, hop_s=HOP_S), sr)


# ------------------------------------------------------------------------ TEO
def teager(x: np.ndarray) -> np.ndarray:
    """Teager-Kaiser energy operator: psi[x](n) = x(n)^2 - x(n-1) x(n+1)."""
    if len(x) < 3:
        return np.zeros_like(x)
    return np.concatenate([[0.0], x[1:-1] ** 2 - x[:-2] * x[2:], [0.0]])


def teo_autoenv(x: np.ndarray, mask: np.ndarray, sr: int = SR) -> float:
    """Simplified TEO-CB-Auto-Env (after Zhou, Hansen & Kaiser 2001).

    For each critical band: TEO profile per speech frame -> normalised
    autocorrelation -> area under its envelope. Regular, unstressed airflow
    gives a smooth TEO profile and a large area; stress-related turbulence
    lowers it. Returns the mean area over bands and speech frames (0-1)."""
    areas = []
    for lo, hi in TEO_BANDS_HZ:
        hi = min(hi, 0.45 * sr)
        sos = butter(2, [lo, hi], btype="bandpass", fs=sr, output="sos")
        frames = frame_signal(sosfiltfilt(sos, x) if len(x) > 64 else x, sr)
        frames = frames[: len(mask)][mask[: len(frames)]]
        for fr in frames:
            t = teager(fr)
            t = t - t.mean()
            e = np.dot(t, t)
            if e < EPS:
                continue
            ac = np.correlate(t, t, mode="full")[len(t) - 1:] / e
            half = ac[: len(ac) // 2]
            areas.append(float(np.mean(np.abs(half))))
    return float(np.mean(areas)) if areas else 0.0


# -------------------------------------------------------------------- summary
def _snr_db(db: np.ndarray, mask: np.ndarray) -> float:
    if mask.sum() == 0:
        return 0.0
    if (~mask).sum() == 0:
        return 40.0
    return float(np.clip(np.median(db[mask]) - np.median(db[~mask]), -10, 60))


def extract(audio: np.ndarray, sr: int = SR, apply_filter: bool = True, denoise: bool = True,
            keep_frames: bool = False) -> UtteranceFeatures:
    """Extract utterance-level features from one mono clip."""
    raw = resample(to_mono_float(np.asarray(audio)), sr, SR)
    sr = SR
    duration = len(raw) / sr
    raw_pow = float(np.mean(raw ** 2)) + EPS
    hum_sos = butter(4, 300, btype="lowpass", fs=sr, output="sos")
    hum = float(np.mean(sosfiltfilt(hum_sos, raw) ** 2)) / raw_pow if len(raw) > 64 else 0.0
    clipped = bool(np.max(np.abs(raw)) >= 0.999) if len(raw) else False

    x = bandpass(raw, sr) if apply_filter else raw
    frames = frame_signal(x, sr)
    db = frame_db(frames)
    mask = vad_mask(db)
    snr = _snr_db(frame_db(frame_signal(raw, sr)), mask)

    f0 = pitch_frames(x, sr)[: len(mask)]
    f0 = np.pad(f0, (0, max(0, len(mask) - len(f0))))
    voiced = mask & (f0 > 0)
    f0v = f0[voiced]
    if f0v.size >= 3:
        # drop octave/harmonic errors: keep values within ~0.6x-1.6x of the median
        med = np.median(f0v)
        f0v = f0v[(f0v > 0.6 * med) & (f0v < 1.6 * med)]

    vals: dict[str, float] = {}
    if f0v.size >= 3:
        # robust range (5th-95th pct) so single octave errors do not dominate
        vals["f0_mean_hz"] = float(np.median(f0v))
        vals["f0_std_hz"] = float(np.std(f0v))
        vals["f0_range_hz"] = float(np.percentile(f0v, 95) - np.percentile(f0v, 5))
        periods = 1.0 / f0v
        vals["jitter_proxy"] = float(np.mean(np.abs(np.diff(periods))) / np.mean(periods))
    else:
        vals.update(f0_mean_hz=0.0, f0_std_hz=0.0, f0_range_hz=0.0, jitter_proxy=0.0)

    sp = mask if mask.any() else np.ones_like(mask)
    npsd = noise_spectrum(frames, mask) if denoise else None
    if npsd is not None:
        # speech level with the steady noise power removed
        n_pow = float(np.mean(frames[~mask] ** 2))
        s_pow = np.maximum(np.mean(frames[sp] ** 2, axis=1) - n_pow, 0.05 * np.mean(frames[sp] ** 2, axis=1))
        db_sp = 10 * np.log10(s_pow + EPS)
    else:
        db_sp = db[sp]
    vals["energy_db_mean"] = float(np.mean(db_sp))
    vals["energy_db_std"] = float(np.std(db[sp]))
    vd = db[voiced] if voiced.sum() >= 3 else db[sp]
    vals["shimmer_proxy_db"] = float(np.mean(np.abs(np.diff(vd)))) if vd.size > 1 else 0.0

    centroid, hf = spectral_stats(frames[sp], sr, noise_psd=npsd)
    vals["spectral_centroid_hz"] = float(np.mean(centroid))
    vals["hf_ratio"] = float(np.mean(hf))

    teo_frames = frame_signal(np.abs(teager(x)), sr)[: len(sp)]
    vals["teo_log_mean"] = float(np.mean(np.log10(teo_frames[sp[: len(teo_frames)]].mean(axis=1) + EPS)))
    vals["teo_autoenv_mean"] = teo_autoenv(x, mask, sr)
    vals["voiced_frac"] = float(voiced.sum() / max(1, mask.sum()))

    cc = mfcc(frames[sp], sr, noise_psd=npsd)
    for i in range(1, N_MFCC):
        vals[f"mfcc_{i}_mean"] = float(np.mean(cc[:, i]))

    q = AudioQuality(duration_s=duration, speech_s=float(mask.sum() * HOP_S), voiced_frac=vals["voiced_frac"],
                     snr_db=snr, low_freq_hum_ratio=hum, clipped=clipped)
    fr = {"db": db, "vad": mask, "f0": f0} if keep_frames else {}
    return UtteranceFeatures(values=vals, quality=q, frames=fr)
