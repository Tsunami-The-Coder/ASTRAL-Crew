# Wearable fixes and current evaluation

2026-11-15. AI-assisted. Owner: wearable workstream. Next integration owner: integration lead.

## Changes
- AST-01 through AST-05 supported in inference, personal baselines and five-member demos.
- Independent periodicity check rejects the reproduced secondary-peak double counting.
- Accepted feature values/units and the shared output format are unchanged; no new dependencies.
- WESAD model refitted as wesad-wrist-logistic-v2-quality-gated; no astronaut calibration.

## Fresh laboratory evaluation
- 15 retained participants; 130 retained windows; 383 rejected signal windows.
- Retained fraction among label-eligible windows: 25.3%.
- Balanced accuracy is estimable for 4 held-out participants: mean 0.6719, SD 0.2226.
- Pooled macro F1 across all retained held-out windows: 0.5469.
- Pooled confusion matrix (rows=true, columns=predicted; non-stress, stress): [[109, 15], [4, 2]].
- Single-class held-out participants remain in pooled evaluation; their balanced accuracy is unavailable.
- Subjects with no retained windows, if any, appear in extraction coverage but cannot contribute predictions.
- This selective coverage is a major limitation. Metrics describe retained laboratory windows only, not all recordings.
- The historical 85.5% used a different window set and must not be presented as this model's performance.

| Participant | Kept | Rejected signal | Excluded label |
|---|---:|---:|---:|
| S2 | 5 | 28 | 68 |
| S3 | 6 | 27 | 75 |
| S4 | 7 | 26 | 74 |
| S5 | 5 | 28 | 71 |
| S6 | 10 | 24 | 83 |
| S7 | 11 | 24 | 52 |
| S8 | 15 | 20 | 56 |
| S9 | 6 | 26 | 55 |
| S10 | 7 | 28 | 56 |
| S11 | 11 | 24 | 52 |
| S13 | 2 | 33 | 57 |
| S14 | 17 | 18 | 57 |
| S15 | 5 | 31 | 51 |
| S16 | 9 | 25 | 59 |
| S17 | 14 | 21 | 63 |

| Held-out participant | Non-stress / stress windows | Balanced accuracy |
|---|---|---|
| S10 | 6 / 1 | 0.7500 |
| S11 | 11 / 0 | Unavailable (single class) |
| S13 | 2 / 0 | Unavailable (single class) |
| S14 | 16 / 1 | 1.0000 |
| S15 | 5 / 0 | Unavailable (single class) |
| S16 | 8 / 1 | 0.4375 |
| S17 | 14 / 0 | Unavailable (single class) |
| S2 | 5 / 0 | Unavailable (single class) |
| S3 | 6 / 0 | Unavailable (single class) |
| S4 | 7 / 0 | Unavailable (single class) |
| S5 | 5 / 0 | Unavailable (single class) |
| S6 | 10 / 0 | Unavailable (single class) |
| S7 | 11 / 0 | Unavailable (single class) |
| S8 | 15 / 0 | Unavailable (single class) |
| S9 | 3 / 3 | 0.5000 |

## Verification and limits
- 41 component/regression tests passed with the final model in 0.624s; zero failures/errors/skips. An earlier final-check process exited without a report; the logged rerun passed.
- Current fusion adapter snapshot accepts all five wearable crew records, preserving null confidence.
- Signal audit: the 1 Hz plus equal second-harmonic waveform is rejected; clean sine rates 45..180 bpm pass within 2 bpm.
- Default fixture demo: five scenarios, five synthetic crew members. No real crew health data in examples.
- Privacy review: no full team names, photos, personal contact details or identifying health records found in wearable files. Published researcher attribution is retained.
- Only wearable files changed. Voice AST-05 handling and dashboard model copies belong to their owners and are not changed here.
- Raw WESAD and derived-feature caches remain local; no data redistribution.
- Signal rejection is not a validated medical quality detector. Summary inputs cannot certify raw-signal quality.
- Real-world stress accuracy, reference-beat accuracy and astronaut validity remain unestablished.

Training: `python -m models.wearable.train <original-WESAD.zip> --output <outside-repo> --trusted-original-wesad`.
Archive SHA256: `5e15d2606adf16d819ba535c1786d92e94bae5ff5392f7ae01fb63f9938fd71c`.
