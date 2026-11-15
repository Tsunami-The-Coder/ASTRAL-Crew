"""Voice stress inference for ASTRAL-Crew. Public API for fusion and backend.

    from models.voice import VoiceStressEstimator

    est = VoiceStressEstimator(baseline_path="data/processed/voice_baselines.json")
    est.enroll("AST-01", ["calm_01.wav", "calm_02.wav", ...])      # once per astronaut
    res = est.analyze_file("comms_0915.wav", crew_id="AST-01",
                           timestamp="2026-11-14T09:15:00Z")
    res.record   # contract record (exactly the 6 DATA_CONTRACT keys) or None
    res.details  # explanation, quality flags, features (optional, for UI/logs)

Contract record (docs/DATA_CONTRACT.md, research/DATA_CONTRACT_PROPOSAL.md):
    {"crew_id": "AST-01", "timestamp": "2026-11-14T09:15:00Z",
     "stress_score": 0.41, "confidence": 0.78, "source": "voice", "data_type": "real"}

No record is produced (record is None) when the astronaut is not speaking,
the audio is invalid, or their baseline is still being enrolled. The data
contract says voice records only exist when someone speaks, so fusion must
already handle missing voice.

CLI:
    python -m models.voice.cli enroll  AST-01 calm1.wav calm2.wav ...
    python -m models.voice.cli analyze AST-01 clip.wav [--timestamp ...]
    python -m models.voice.cli analyze-dir AST-01 folder/ --out voice.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np

from . import scoring
from .baseline import BaselineStore, CrewBaseline
from .features import SR, extract, load_wav

CREW_IDS = {"AST-01", "AST-02", "AST-03", "AST-04", "AST-05"}
CONTRACT_KEYS = ("crew_id", "timestamp", "stress_score", "confidence", "source", "data_type")
ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
MIN_SPEECH_S = 1.0
MIN_ENROLL = 5
DEFAULT_BASELINES = Path("data/processed/voice_baselines.json")  # git-ignored by data/ layer
METHOD = "personal_baseline_v1"


@dataclass
class VoiceResult:
    record: dict | None
    details: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.record is not None


def normalise_timestamp(ts: str | datetime | None) -> str:
    if ts is None:
        ts = datetime.now(timezone.utc)
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    s = str(ts).strip()
    if ISO_Z.match(s):
        return s
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(f"timestamp '{ts}' is not ISO-8601") from e
    return normalise_timestamp(dt)


def make_record(crew_id: str, timestamp: str, stress_score: float, confidence: float, data_type: str) -> dict:
    """The ONLY place a contract record is built, so the schema cannot drift."""
    return {"crew_id": crew_id, "timestamp": timestamp,
            "stress_score": round(float(np.clip(stress_score, 0, 1)), 3),
            "confidence": round(float(np.clip(confidence, 0, 1)), 3),
            "source": "voice", "data_type": data_type}


class VoiceStressEstimator:
    def __init__(self, baseline_path: str | Path | None = None, model_path: str | Path | None = scoring.MODEL_PATH,
                 min_enroll: int = MIN_ENROLL, auto_enroll: bool = True):
        self.store = BaselineStore(baseline_path)
        self.model = scoring.load_model(Path(model_path)) if model_path else None
        self.min_enroll = min_enroll
        self.auto_enroll = auto_enroll

    # ---------------------------------------------------------- enrollment
    def enroll(self, crew_id: str, clips: Iterable[np.ndarray | str | Path], sr: int = SR,
               data_type: str = "real", replace: bool = False) -> CrewBaseline:
        """Build or extend an astronaut's calm-voice baseline from clips (arrays or WAV paths)."""
        self._check_crew(crew_id)
        if replace:
            self.store.reset(crew_id)
        b = self.store.get_or_create(crew_id, data_type)
        used = 0
        for clip in clips:
            audio = load_wav(clip) if isinstance(clip, (str, Path)) else np.asarray(clip, dtype=np.float32)
            f = extract(audio, SR if isinstance(clip, (str, Path)) else sr)
            if f.quality.speech_s >= MIN_SPEECH_S:
                b.add(f)
                used += 1
        if used == 0:
            raise ValueError(f"No usable speech in enrollment clips for {crew_id}")
        self.store.save()
        return b

    # ------------------------------------------------------------ analysis
    def analyze(self, audio: np.ndarray, crew_id: str, timestamp: str | datetime | None = None,
                sr: int = SR, data_type: str = "real") -> VoiceResult:
        """Score one utterance. Never raises on bad audio; returns record=None with a reason."""
        details: dict = {"method": METHOD, "crew_id": crew_id}
        try:
            self._check_crew(crew_id)
            ts = normalise_timestamp(timestamp)
            if data_type not in ("real", "synthetic"):
                raise ValueError("data_type must be 'real' or 'synthetic'")
        except ValueError as e:
            return VoiceResult(None, {**details, "status": "invalid_input", "reason": str(e)})
        details["timestamp"] = ts

        audio = np.asarray(audio, dtype=np.float32).ravel()
        if audio.size == 0 or not np.all(np.isfinite(audio)):
            return VoiceResult(None, {**details, "status": "invalid_input", "reason": "empty or non-finite audio"})

        feats = extract(audio, sr)
        details["quality"] = feats.quality.as_dict()
        if feats.quality.speech_s < MIN_SPEECH_S or feats.values["f0_mean_hz"] == 0:
            return VoiceResult(None, {**details, "status": "no_speech",
                                      "reason": f"speech {feats.quality.speech_s:.2f}s < {MIN_SPEECH_S}s or no voiced frames"})

        b = self.store.get(crew_id)
        if b is None or b.n < self.min_enroll:
            if self.auto_enroll:
                b = self.store.get_or_create(crew_id, data_type)
                b.add(feats)
                self.store.save()
            return VoiceResult(None, {**details, "status": "enrolling_baseline",
                                      "reason": f"baseline has {b.n if b else 0}/{self.min_enroll} utterances",
                                      "baseline_n": b.n if b else 0})

        z = b.z(feats)
        rule = scoring.rule_score(z)
        score = rule
        model_used = False
        if self.model is not None:
            score = 0.5 * rule + 0.5 * scoring.model_score(self.model, z)
            model_used = True
        mismatch = scoring.profile_distance(z)
        conf, flags = scoring.confidence(feats.quality, b.n, mismatch, model_used)
        record = make_record(crew_id, ts, score, conf, data_type)
        details.update(
            status="ok", baseline_n=b.n, model_used=model_used,
            rule_score=round(rule, 3), arousal_deviation_sd=round(scoring.weighted_deviation(z), 3),
            profile_distance=round(mismatch, 3), flags=flags,
            top_contributors=scoring.top_contributors(z),
            explanation=scoring.explanation(z, score),
            features={k: round(v, 4) for k, v in feats.values.items()},
        )
        return VoiceResult(record, details)

    def analyze_file(self, path: str | Path, crew_id: str, timestamp: str | datetime | None = None,
                     data_type: str = "real") -> VoiceResult:
        try:
            audio = load_wav(path)
        except Exception as e:  # unreadable file is an input problem, not a crash
            return VoiceResult(None, {"method": METHOD, "crew_id": crew_id, "status": "invalid_input",
                                      "reason": f"cannot read {path}: {e}"})
        res = self.analyze(audio, crew_id, timestamp, SR, data_type)
        res.details["file"] = str(path)
        return res

    @staticmethod
    def _check_crew(crew_id: str) -> None:
        if crew_id not in CREW_IDS:
            raise ValueError(f"crew_id '{crew_id}' not in {sorted(CREW_IDS)}")


def write_jsonl(records: Iterable[dict], path: str | Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            if r is not None:
                f.write(json.dumps(r) + "\n")
                n += 1
    return n


# ------------------------------------------------------------------- CLI
def _cli() -> None:
    ap = argparse.ArgumentParser(description="ASTRAL-Crew voice stress indicator")
    ap.add_argument("--baselines", type=Path, default=DEFAULT_BASELINES)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enroll", help="build a calm-voice baseline")
    e.add_argument("crew_id")
    e.add_argument("wavs", nargs="+", type=Path)
    e.add_argument("--replace", action="store_true")
    a = sub.add_parser("analyze", help="score one WAV")
    a.add_argument("crew_id")
    a.add_argument("wav", type=Path)
    a.add_argument("--timestamp")
    a.add_argument("--data-type", default="real", choices=["real", "synthetic"])
    d = sub.add_parser("analyze-dir", help="score every WAV in a folder (sorted by name)")
    d.add_argument("crew_id")
    d.add_argument("folder", type=Path)
    d.add_argument("--out", type=Path, default=Path("data/processed/voice_outputs.jsonl"))
    d.add_argument("--data-type", default="real", choices=["real", "synthetic"])
    args = ap.parse_args()

    est = VoiceStressEstimator(args.baselines)
    if args.cmd == "enroll":
        b = est.enroll(args.crew_id, args.wavs, replace=args.replace)
        print(f"{args.crew_id}: baseline now has {b.n} utterances -> {args.baselines}")
    elif args.cmd == "analyze":
        r = est.analyze_file(args.wav, args.crew_id, args.timestamp, args.data_type)
        print(json.dumps({"record": r.record, "details": r.details}, indent=2))
    else:
        recs = []
        for p in sorted(args.folder.rglob("*.wav")):
            r = est.analyze_file(p, args.crew_id, None, args.data_type)
            print(f"{p.name:<40} {r.details.get('status'):<20} {r.record['stress_score'] if r.ok else ''}")
            recs.append(r.record)
        print(f"{write_jsonl(recs, args.out)} records -> {args.out}")


if __name__ == "__main__":
    _cli()

