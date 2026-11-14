"""Run the voice pipeline on REAL NASA Artemis II crew audio (demonstration only).

Artemis audio is real spaceflight speech but has NO stress labels
(research/SCIENCE_REVIEW.md item 2). So this script:
  * shows the band-pass filter removing low-frequency noise
    (before/after spectrogram PNG),
  * extracts the features (pitch, TEO, MFCC, ...) for every clip,
  * reports each clip's deviation from a reference built from the first
    clips in the set, with neutral wording,
and it does NOT label any astronaut as stressed and does NOT report accuracy.
Say: "Demonstrated on authentic Artemis II crew audio from NASA's Artemis
Audio Library." Never say "validated".

Prepare audio (Eleni's audio_manifest.py does steps 2-3 for you):
    1. download clips from https://www.nasa.gov/artemisaudio into data/raw/audio/artemis2/
    2. for f in *.mp3; do ffmpeg -i "$f" -ac 1 -ar 16000 "${f%.mp3}.wav"; done
    3. python -m data.scripts.audio_manifest --in data/raw/audio/artemis2 \
           --source "NASA Artemis Audio Library (Artemis II)" --license "NASA media usage guidelines"

Then:
    python -m models.voice.artemis_demo                      # uses data/processed/audio/manifest.csv
    python -m models.voice.artemis_demo --in some/folder     # or any folder of WAVs
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .baseline import CrewBaseline
from .features import FEATURE_NAMES, SR, bandpass, extract, load_wav
from .scoring import AROUSAL_WEIGHTS, READABLE, weighted_deviation

DEFAULT_MANIFEST = Path("data/processed/audio/manifest.csv")
OUT = Path("data/processed/voice_artemis")


def list_clips(inp: Path | None, manifest: Path) -> list[Path]:
    if inp:
        return sorted(inp.rglob("*.wav"))
    if manifest.exists():
        return [Path(p) for p in pd.read_csv(manifest)["file"]]
    raise SystemExit(f"No --in folder given and {manifest} not found (see docstring).")


def spectrogram_png(audio: np.ndarray, path: Path, title: str) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: skipping spectrogram (pip install matplotlib)")
        return False
    seg = audio[: SR * 10]
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True)
    for ax, (sig, name) in zip(axes, [(seg, "raw"), (bandpass(seg), "after 300-3400 Hz Butterworth band-pass")]):
        ax.specgram(sig, NFFT=512, Fs=SR, noverlap=384, cmap="magma", vmin=-140)
        ax.set_ylim(0, 4500)
        ax.axhline(300, color="cyan", lw=0.8, ls="--")
        ax.axhline(3400, color="cyan", lw=0.8, ls="--")
        ax.set_ylabel("Hz")
        ax.set_title(name, fontsize=9)
    axes[-1].set_xlabel("seconds")
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


def run(clips: list[Path], n_reference: int = 3, out: Path = OUT, data_type: str = "real",
        source: str = "NASA Artemis Audio Library (Artemis II)") -> pd.DataFrame:
    rows, feats = [], []
    for p in clips:
        audio = load_wav(p)
        f = extract(audio)
        feats.append(f)
        rows.append({"file": p.as_posix(), **f.quality.as_dict(), **{k: round(v, 4) for k, v in f.values.items()}})
    df = pd.DataFrame(rows)
    usable = [i for i, f in enumerate(feats) if f.quality.speech_s >= 1.0]
    ref_idx = usable[:n_reference]
    if len(ref_idx) >= 2:
        ref = CrewBaseline(crew_id="artemis-reference", vectors=[feats[i].vector().tolist() for i in ref_idx])
        dev, top = [], []
        for i, f in enumerate(feats):
            if i not in usable:
                dev.append(np.nan)
                top.append("too little speech")
                continue
            z = ref.z(f)
            dev.append(round(weighted_deviation(z), 2))
            k = max(AROUSAL_WEIGHTS, key=lambda n: abs(z[n]))
            top.append(f"{READABLE[k]} {z[k]:+.1f} SD")
        df["deviation_from_reference_sd"] = dev
        df["largest_change"] = top
        df["is_reference_clip"] = [i in ref_idx for i in range(len(feats))]
    df["source"] = source
    df["data_type"] = data_type
    df["stress_label"] = "none"  # no ground truth exists for this audio
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "artemis_voice_features.csv", index=False)
    if clips:
        spectrogram_png(load_wav(clips[0]), out / "filter_before_after.png", f"{clips[0].name}  ({source})")
    meta = {"clips": len(clips), "usable": len(usable), "reference_clips": [clips[i].name for i in ref_idx],
            "note": "Demonstration on real crew audio. No stress labels; deviation is NOT a stress claim.",
            "feature_names": FEATURE_NAMES}
    (out / "README.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", type=Path)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--n-reference", type=int, default=3)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    df = run(list_clips(a.inp, a.manifest), a.n_reference, a.out)
    cols = [c for c in ["file", "speech_s", "snr_db", "f0_mean_hz", "teo_autoenv_mean",
                        "deviation_from_reference_sd", "largest_change"] if c in df]
    print(df[cols].to_string(index=False))
    print(f"\n-> {a.out}/artemis_voice_features.csv, filter_before_after.png")
    print("Reminder: real audio, no stress labels. Demonstration, not validation.")


if __name__ == "__main__":
    main()
