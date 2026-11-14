"""Personal voice baseline ("Digital Health Twin" for the voice channel).

Each astronaut enrolls a few utterances of normal, calm speech (e.g. routine
comms). New speech is then scored by how far it deviates from THAT person's
own baseline, not from a population norm. This is the strategy recommended in
research/SCIENCE_REVIEW.md item 1, because we have no labelled astronaut
stress speech.

The baseline is stored as JSON (offline, no database needed). The backend can
copy it into SQLite if it wants; the format is plain numbers.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .features import FEATURE_NAMES, UtteranceFeatures

# Minimum standard deviation per feature, so a very consistent baseline does
# not turn tiny changes into huge z-scores. team_assumption, chosen from the
# typical within-speaker spread of each measure.
STD_FLOOR = {
    "f0_mean_hz": 4.0, "f0_std_hz": 3.0, "f0_range_hz": 8.0, "jitter_proxy": 0.005,
    "energy_db_mean": 1.5, "energy_db_std": 0.5, "shimmer_proxy_db": 0.3,
    "spectral_centroid_hz": 30.0, "hf_ratio": 0.01,
    "teo_log_mean": 0.1, "teo_autoenv_mean": 0.01, "voiced_frac": 0.03,
}
MFCC_STD_FLOOR = 0.5
MAX_ENROLLMENT = 60  # keep the most recent N calm utterances
Z_CLIP = 6.0


def _floor(name: str) -> float:
    return STD_FLOOR.get(name, MFCC_STD_FLOOR)


@dataclass
class CrewBaseline:
    crew_id: str
    vectors: list[list[float]] = field(default_factory=list)  # enrollment feature vectors
    data_type: str = "real"
    updated: str = ""

    @property
    def n(self) -> int:
        return len(self.vectors)

    def add(self, feats: UtteranceFeatures) -> None:
        self.vectors.append([round(float(v), 6) for v in feats.vector()])
        self.vectors = self.vectors[-MAX_ENROLLMENT:]
        self.updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def stats(self) -> tuple[np.ndarray, np.ndarray]:
        if not self.vectors:
            raise ValueError(f"Baseline for {self.crew_id} is empty")
        m = np.asarray(self.vectors, dtype=float)
        mean = m.mean(axis=0)
        sd = m.std(axis=0, ddof=1) if len(m) > 1 else np.zeros(m.shape[1])
        floors = np.array([_floor(k) for k in FEATURE_NAMES])
        return mean, np.maximum(sd, floors)

    def z(self, feats: UtteranceFeatures) -> dict[str, float]:
        mean, sd = self.stats()
        zz = np.clip((feats.vector() - mean) / sd, -Z_CLIP, Z_CLIP)
        return {k: float(v) for k, v in zip(FEATURE_NAMES, zz)}

    def summary(self) -> dict:
        mean, sd = self.stats()
        return {"crew_id": self.crew_id, "n_utterances": self.n, "updated": self.updated,
                "data_type": self.data_type,
                "mean": {k: round(float(v), 4) for k, v in zip(FEATURE_NAMES, mean)},
                "std": {k: round(float(v), 4) for k, v in zip(FEATURE_NAMES, sd)}}


class BaselineStore:
    """All crew baselines, persisted to one JSON file (or kept in memory if path=None)."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._b: dict[str, CrewBaseline] = {}
        if self.path and self.path.exists():
            self.load()

    def get(self, crew_id: str) -> CrewBaseline | None:
        return self._b.get(crew_id)

    def get_or_create(self, crew_id: str, data_type: str = "real") -> CrewBaseline:
        if crew_id not in self._b:
            self._b[crew_id] = CrewBaseline(crew_id=crew_id, data_type=data_type)
        return self._b[crew_id]

    def crew(self) -> list[str]:
        return sorted(self._b)

    def reset(self, crew_id: str) -> None:
        self._b.pop(crew_id, None)

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"feature_names": FEATURE_NAMES, "baselines": {k: asdict(v) for k, v in self._b.items()}}
        self.path.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    def load(self) -> None:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("feature_names") != FEATURE_NAMES:
            raise ValueError(f"{self.path}: baseline was built with a different feature set; re-enroll the crew")
        self._b = {k: CrewBaseline(**v) for k, v in payload["baselines"].items()}
