"""Train and evaluate the optional learned voice-arousal model on RAVDESS.

Requires the RAVDESS manifest from the research lead's data layer:
    # 1. download Audio_Speech_Actors_01-24.zip (~215 MB) from https://zenodo.org/records/1188976
    # 2. unzip into data/raw/RAVDESS/
    python -m data.scripts.ravdess_prepare --in data/raw/RAVDESS
    python -m models.voice.train                       # evaluate + save model.json

Design (matches our Digital Twin idea and avoids leakage):
  * For every actor, a personal baseline is built ONLY from their "neutral"
    clips (4 per actor). Those clips are never scored.
  * The remaining clips are scored as z-scores against that baseline:
    calm = label 0 (low arousal), angry/fearful = label 1 (high arousal).
  * Evaluation is actor-independent: the research lead's 6 actor folds; train on 5 folds
    of actors, test on actors the model never heard.
  * Reported: balanced accuracy and F1 per fold (mean +- SD and worst fold),
    for (a) the hand-set rule score alone and (b) logistic regression.

HONEST FRAMING: RAVDESS is ACTED emotion. Report it as
"high-arousal acted speech as a stress proxy", never as astronaut stress.
Results are written to models/voice/results/ravdess_eval.json; copy the
numbers into VALIDATION.md only after you have actually run this.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import scoring
from .baseline import CrewBaseline
from .features import FEATURE_NAMES, extract, load_wav

HERE = Path(__file__).resolve().parent


def featurise(manifest: pd.DataFrame, root: Path | None = None) -> pd.DataFrame:
    """Extract features for every clip in the manifest (one row per clip)."""
    rows = []
    for i, r in enumerate(manifest.itertuples(index=False), 1):
        path = Path(r.file) if root is None else root / Path(r.file).name
        f = extract(load_wav(path))
        rows.append({**r._asdict(), **f.values, "speech_s": f.quality.speech_s})
        if i % 100 == 0:
            print(f"  features: {i}/{len(manifest)}")
    return pd.DataFrame(rows)


def baseline_z(df: pd.DataFrame) -> pd.DataFrame:
    """Per-actor z-scores against that actor's neutral clips; neutral clips are dropped."""
    out = []
    for actor, g in df.groupby("actor"):
        enroll = g[g["emotion"] == "neutral"]
        test = g[g["emotion"] != "neutral"]
        if len(enroll) < 2 or test.empty:
            continue
        b = CrewBaseline(crew_id=f"actor-{actor}", vectors=enroll[FEATURE_NAMES].values.tolist())
        mean, sd = b.stats()
        z = np.clip((test[FEATURE_NAMES].values - mean) / sd, -6, 6)
        zt = pd.DataFrame(z, columns=FEATURE_NAMES, index=test.index)
        out.append(pd.concat([test[["actor", "fold", "emotion", "intensity", "high_arousal"]], zt], axis=1))
    return pd.concat(out)


def _metrics(y: np.ndarray, p: np.ndarray) -> dict:
    from sklearn.metrics import balanced_accuracy_score, f1_score
    yhat = (p >= 0.5).astype(int)
    return {"balanced_accuracy": float(balanced_accuracy_score(y, yhat)), "f1_high_arousal": float(f1_score(y, yhat)),
            "n": int(len(y))}


def evaluate(zdf: pd.DataFrame, C: float = 1.0) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    per_fold = []
    for k in sorted(zdf["fold"].unique()):
        tr, te = zdf[zdf.fold != k], zdf[zdf.fold == k]
        sc = StandardScaler().fit(tr[FEATURE_NAMES].values)
        clf = LogisticRegression(C=C, max_iter=2000, class_weight="balanced").fit(
            sc.transform(tr[FEATURE_NAMES].values), tr.high_arousal.values)
        p_lr = clf.predict_proba(sc.transform(te[FEATURE_NAMES].values))[:, 1]
        p_rule = np.array([scoring.rule_score(dict(zip(FEATURE_NAMES, row))) for row in te[FEATURE_NAMES].values])
        per_fold.append({"fold": int(k), "test_actors": sorted(int(a) for a in te.actor.unique()),
                         "logreg": _metrics(te.high_arousal.values, p_lr),
                         "rule": _metrics(te.high_arousal.values, p_rule)})

    def agg(kind: str) -> dict:
        ba = np.array([f[kind]["balanced_accuracy"] for f in per_fold])
        f1 = np.array([f[kind]["f1_high_arousal"] for f in per_fold])
        return {"balanced_accuracy_mean": round(float(ba.mean()), 4), "balanced_accuracy_sd": round(float(ba.std()), 4),
                "balanced_accuracy_worst_fold": round(float(ba.min()), 4),
                "f1_mean": round(float(f1.mean()), 4), "f1_sd": round(float(f1.std()), 4)}

    return {"per_fold": per_fold, "summary": {"logreg": agg("logreg"), "rule": agg("rule")}}


def fit_final(zdf: pd.DataFrame, C: float = 1.0) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(zdf[FEATURE_NAMES].values)
    clf = LogisticRegression(C=C, max_iter=2000, class_weight="balanced").fit(
        sc.transform(zdf[FEATURE_NAMES].values), zdf.high_arousal.values)
    return {"feature_names": FEATURE_NAMES, "scaler_mean": sc.mean_.tolist(), "scaler_scale": sc.scale_.tolist(),
            "coef": clf.coef_[0].tolist(), "intercept": float(clf.intercept_[0]),
            "trained_on": "RAVDESS speech (acted), per-actor neutral baseline z-scores; calm=0, angry/fearful=1",
            "n_clips": int(len(zdf)), "n_actors": int(zdf.actor.nunique()),
            "trained_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "license_note": "RAVDESS CC BY-NC-SA 4.0; cite Livingstone & Russo (2018)"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=Path("data/processed/ravdess_manifest.csv"))
    ap.add_argument("--features-cache", type=Path, default=Path("data/processed/ravdess_voice_features.csv"))
    ap.add_argument("--out-model", type=Path, default=HERE / "model.json")
    ap.add_argument("--out-results", type=Path, default=HERE / "results" / "ravdess_eval.json")
    ap.add_argument("--no-save-model", action="store_true", help="evaluate only")
    a = ap.parse_args()

    if not a.manifest.exists():
        raise SystemExit(f"{a.manifest} not found. Run: python -m data.scripts.ravdess_prepare --in data/raw/RAVDESS")
    man = pd.read_csv(a.manifest)
    if a.features_cache.exists():
        feats = pd.read_csv(a.features_cache)
        print(f"Using cached features {a.features_cache}")
    else:
        print(f"Extracting features for {len(man)} clips ...")
        feats = featurise(man)
        a.features_cache.parent.mkdir(parents=True, exist_ok=True)
        feats.to_csv(a.features_cache, index=False)
    zdf = baseline_z(feats)
    res = evaluate(zdf)
    res["dataset"] = {"name": "RAVDESS (acted)", "clips_scored": int(len(zdf)), "actors": int(zdf.actor.nunique()),
                      "label_counts": zdf.high_arousal.value_counts().to_dict()}
    a.out_results.parent.mkdir(parents=True, exist_ok=True)
    a.out_results.write_text(json.dumps(res, indent=2, default=int), encoding="utf-8")
    print(json.dumps(res["summary"], indent=2))
    print(f"Per-fold results -> {a.out_results}")
    if not a.no_save_model:
        a.out_model.write_text(json.dumps(fit_final(zdf), indent=1), encoding="utf-8")
        print(f"Model -> {a.out_model}  (inference will now average rule + model)")


if __name__ == "__main__":
    main()
