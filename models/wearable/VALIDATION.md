# Verification evidence

Date: 2026-11-14. Owner: Khalid. AI-assisted implementation.

## Component tests

Command, from repository root:

```text
python -m unittest models.wearable.test_wearable -v
```

Completed: **31 tests passed; zero skips, failures or errors** (0.382s test runtime,
excluding imports). Tested with Python 3.12 and optional training dependencies
numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1.

Coverage includes missing/invalid values; JSON-safe results; timezone normalization;
future/stale/short windows; feature-pipeline/window incompatibility; inert model
load/export; comparison with sklearn prediction; no input mutation; baseline
person/provenance/date separation; no duplicate calibration windows; context-only
sleep/self-report; motion caution; raw-signal rejection; pulse extraction on a known
waveform; label boundaries; participant-disjoint folds; five four-person scenarios.

Initial test execution had a local temporary-folder permission error. It passed
after selecting a writable temporary folder; the final run above is the result.

## Offline synthetic demonstration

```text
python -m models.wearable.demo --output ../wearable-demo
```

Completed using Python `-S` (site packages disabled): five scenarios and 20 crew results exported as JSON and a readable
HTML report. Every input is synthetic; the default fixture coefficients are
hand-authored and are not a trained research model. The scenarios are interface
checks, not proof of physiological or clinical validity.
The HTML was generated but could not be visually inspected: browser control
ended because the current browser URL could not be reliably determined.

## Original research data

Downloaded original WESAD.zip through the link on the authors' University of
Siegen page. Archive size: 2,249,444,501 bytes.

SHA256: `5e15d2606adf16d819ba535c1786d92e94bae5ff5392f7ae01fb63f9938fd71c`.

Inspected the original `WESAD/wesad_readme.pdf` in full. Confirmed subject IDs,
dictionary structure, wrist sample rates/units, synchronized 700Hz labels and
the label mapping used by the implementation. No raw participant records are
committed or redistributed.

Completed original WESAD run: 15 participants, 472 retained non-overlapping 60-second windows.

Mean participant balanced accuracy: **0.8546**. Between-participant SD: **0.1256**.

Pooled macro F1: **0.8308**.

Confusion matrix (rows=true, columns=predicted; non-stress, stress): `[[274, 50], [22, 126]]`.

| Held-out participant | Test windows | Balanced accuracy | Macro F1 |
|---|---:|---:|---:|
| S10 | 35 | 0.8125 | 0.7395 |
| S11 | 32 | 1.0000 | 1.0000 |
| S13 | 35 | 0.6000 | 0.4167 |
| S14 | 35 | 0.9800 | 0.9660 |
| S15 | 34 | 0.6958 | 0.6900 |
| S16 | 33 | 0.9565 | 0.9318 |
| S17 | 35 | 0.9792 | 0.9676 |
| S2 | 33 | 0.9500 | 0.9630 |
| S3 | 33 | 0.6783 | 0.6980 |
| S4 | 17 | 0.9444 | 0.9412 |
| S5 | 31 | 0.8864 | 0.8272 |
| S6 | 29 | 0.9237 | 0.9237 |
| S7 | 28 | 0.9167 | 0.8893 |
| S8 | 35 | 0.7727 | 0.8058 |
| S9 | 27 | 0.7222 | 0.7336 |

These are ground-laboratory cross-validation results, not astronaut or clinical validation. Scores are uncalibrated. No hyperparameters were selected using these held-out results.

Command: `python -m models.wearable.train <original-WESAD.zip> --output <outside-repo> --trusted-original-wesad`. The complete local evaluation report records per-subject exclusions and archive SHA256. Raw data and model weights are not committed.

## Integration status

Component and fixture checks only. No full-app end-to-end test is claimed:
the inspected fusion/backend/UI workstreams contained planning documents and
the shared handoff is still proposed. Colin must review the interface and run
the integration checks in COLIN_HANDOFF.md. No changes were made outside this
wearable workstream, and no code was merged into main.
