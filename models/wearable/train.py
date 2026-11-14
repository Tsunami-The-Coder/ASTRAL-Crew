"""Participant-independent WESAD baseline and inert JSON model export.

AI-assisted. Raw archive and trained artifacts must stay outside the repository.
Only process the original trusted WESAD archive: pickle can execute code.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pickle
import re
import zipfile
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .inference import FEATURES
from .signals import extract_window, FEATURE_PIPELINE

SUBJECTS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17]


def window_label(labels):
    """Keep homogeneous windows: 1=baseline, 2=stress, 3=amusement.

    0/transitions, 4/meditation, 5..7/ignored are excluded. Mapping must agree
    with the original archive readme. No majority vote across transitions.
    """
    labels = np.asarray(labels).reshape(-1)
    if labels.size != 42000 or not np.all(labels == labels[0]) or labels[0] not in (1, 2, 3):
        return None
    return int(labels[0] == 2)


def extract_archive(archive_path):
    rows, audit = [], []
    with zipfile.ZipFile(archive_path) as archive:
        for subject in SUBJECTS:
            name = next((n for n in archive.namelist() if re.search(rf"(?:^|/)S{subject}/S{subject}\.pkl$", n)), None)
            if name is None:
                raise ValueError(f"missing original subject S{subject}")
            print(f"Extracting S{subject}", flush=True)
            with archive.open(name) as stream:
                data = pickle.load(stream, encoding="latin1")
            if str(data["subject"]) != f"S{subject}":
                raise ValueError("subject identity mismatch")
            labels = data["label"]
            wrist = data["signal"]["wrist"]
            kept = rejected = excluded = 0
            for start in range(0, len(labels) - 42000 + 1, 42000):
                label = window_label(labels[start:start + 42000])
                if label is None:
                    excluded += 1
                    continue
                second = start // 700
                try:
                    features = extract_window(wrist["BVP"][second*64:(second+60)*64],
                                              wrist["EDA"][second*4:(second+60)*4],
                                              wrist["ACC"][second*32:(second+60)*32])
                except ValueError:
                    rejected += 1
                    continue
                rows.append({"subject_id": f"S{subject}", "start_seconds": second,
                             "label": label, "features": features})
                kept += 1
            audit.append({"subject": f"S{subject}", "kept_windows": kept,
                          "signal_rejected": rejected, "label_excluded": excluded})
            del data, wrist, labels
    return rows, audit


def subject_folds(groups):
    groups = np.asarray(groups)
    subjects = np.unique(groups)
    if len(subjects) < 3:
        raise ValueError("at least three participants required")
    for subject in subjects:
        yield subject, np.flatnonzero(groups != subject), np.flatnonzero(groups == subject)


def _pipeline():
    # Fixed baseline: no hyperparameter selection on held-out participants.
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=42))


def evaluate(rows):
    x = np.asarray([[row["features"][key] for key in FEATURES] for row in rows], dtype=float)
    y = np.asarray([row["label"] for row in rows], dtype=int)
    groups = np.asarray([row["subject_id"] for row in rows])
    if x.ndim != 2 or not np.isfinite(x).all() or set(y) != {0, 1}:
        raise ValueError("finite features and both target classes required")
    predictions = np.empty_like(y)
    folds = []
    for subject, train, test in subject_folds(groups):
        if set(y[train]) != {0, 1} or set(y[test]) != {0, 1}:
            raise ValueError("every fold needs both classes for balanced evaluation")
        pipeline = _pipeline().fit(x[train], y[train])
        predicted = pipeline.predict(x[test])
        predictions[test] = predicted
        folds.append({"held_out_subject": subject, "train_subjects": sorted(set(groups[train])),
                      "train_windows": len(train), "test_windows": len(test),
                      "balanced_accuracy": float(balanced_accuracy_score(y[test], predicted)),
                      "macro_f1": float(f1_score(y[test], predicted, average="macro", zero_division=0))})
    report = {
        "evaluation": "leave_one_subject_out", "feature_pipeline": FEATURE_PIPELINE,
        "data_origin": "research", "dataset": "WESAD", "n_subjects": len(set(groups)), "n_windows": len(rows),
        "target": "stress (2) vs baseline/amusement (1/3)",
        "threshold": 0.5, "threshold_role": "fixed classifier boundary; not a medical threshold",
        "folds": folds,
        "mean_subject_balanced_accuracy": float(np.mean([f["balanced_accuracy"] for f in folds])),
        "std_subject_balanced_accuracy": float(np.std([f["balanced_accuracy"] for f in folds])),
        "pooled_macro_f1": float(f1_score(y, predictions, average="macro", zero_division=0)),
        "confusion_matrix_labels": ["non_stress", "stress"],
        "pooled_confusion_matrix": confusion_matrix(y, predictions, labels=[0, 1]).tolist(),
        "limitations": ["15-person ground laboratory dataset; not astronaut validation.",
                        "No independent external dataset or calibrated probabilities.",
                        "Pulse-derived RMSSD is not ECG-derived HRV.",
                        "No subject-specific adaptation in held-out evaluation."],
        "ai_assisted": True,
    }
    final = _pipeline().fit(x, y)
    scaler, estimator = final.steps[0][1], final.steps[1][1]
    model = {"format": "astral-logistic-v1", "version": "wesad-wrist-logistic-v1",
             "features": list(FEATURES), "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
             "weights": estimator.coef_[0].tolist(), "intercept": float(estimator.intercept_[0]),
             "training_data_origin": "research", "dataset": "WESAD", "feature_pipeline": FEATURE_PIPELINE,
             "ai_assisted": True}
    return model, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Local path OUTSIDE repository")
    parser.add_argument("--trusted-original-wesad", action="store_true", help="Confirm original archive source before pickle deserialization")
    args = parser.parse_args()
    if not args.trusted_original_wesad:
        parser.error("only load an original trusted WESAD archive; pass --trusted-original-wesad")
    repo = Path(__file__).resolve().parents[2]
    if args.output.resolve().is_relative_to(repo):
        parser.error("trained artifacts/raw features must be outside the repository")
    args.output.mkdir(parents=True, exist_ok=True)
    with args.archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    rows, audit = extract_archive(args.archive)
    model, report = evaluate(rows)
    report.update(archive_sha256=digest, extraction_audit=audit)
    model["archive_sha256"] = digest
    for name, value in (("model.json", model), ("evaluation.json", report)):
        (args.output / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("n_subjects", "n_windows", "mean_subject_balanced_accuracy", "pooled_macro_f1")}), flush=True)


if __name__ == "__main__":
    main()
