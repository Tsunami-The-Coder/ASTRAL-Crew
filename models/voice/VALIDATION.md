# Validation: what was actually measured (voice)

Run on 14 Nov 2026 with Python 3.13, numpy 2.5, scipy 1.18. Every number here comes from a script in this folder and can be re-run.

> **All audio used so far is SYNTHETIC** (`synth.py`, a source-filter speech model). These results test the code, the noise handling and the scoring logic. They say **nothing** about accuracy on real human stress. No real-stress or RAVDESS accuracy exists yet.

## 1. Automated tests
`python -m pytest models/voice -q` → **28 passed** (~15 s).
Together with the research lead's data tests: `python -m pytest tests models/voice -q` → **48 passed**.

Covered: band-pass removes 60 Hz hum by > 30 dB and keeps 1 kHz (< 1 dB loss); pitch within 3 % at 110 and 200 Hz; Teager energy identity; resampling from 44.1 kHz; records have exactly the 6 contract keys and pass the research lead's `check_outputs`; silence, noise-only, NaN, empty, unreadable files, unknown crew, bad timestamps → no record and no crash; auto-enrollment; calm < 0.4 and aroused > 0.6 for all four synthetic speakers; a naturally high voice is not flagged; save/load of baselines; low SNR lowers confidence; RAVDESS training pipeline runs end to end on fake RAVDESS-named files; scenario demo output validates; Artemis demo writes no stress labels.

## 2. Full pipeline on the research lead's nine scenarios (`demo.py --all --snr 15`)
For every voice event in `data/scenarios/*/voice_events.csv`, a synthetic utterance with the scenario's assumed arousal was generated, mixed with cabin noise at 15 dB SNR, and run through the real pipeline (8 calm enrollment clips per astronaut).

| Scenario | Records | All valid | r (intended vs. pipeline) | Mean score, calm | Mean score, stressed | Calm utterances ≥ 0.6 |
|---|---|---|---|---|---|---|
| 01_nominal | 289 | ✅ | 0.513 | 0.247 | – | 6/287 (2.1 %) |
| 02_co2_scrubber_failure | 342 | ✅ | 0.884 | 0.263 | 0.896 | 7/161 (4.3 %) |
| 03_solar_particle_event | 356 | ✅ | 0.871 | 0.260 | 0.926 | 9/238 (3.8 %) |
| 04_cabin_depressurization | 337 | ✅ | 0.799 | 0.271 | 0.839 | 12/232 (5.2 %) |
| 05_emotional_contagion | 345 | ✅ | 0.917 | 0.251 | 0.952 | 10/227 (4.4 %) |
| 06_sensor_fault | 372 | ✅ | 0.610 | 0.229 | – | 4/360 (1.1 %) |
| 07_exercise_session | 303 | ✅ | 0.466 | 0.225 | – | 4/294 (1.4 %) |
| 08_individual_red_alert | 349 | ✅ | 0.882 | 0.220 | 0.992 | 6/315 (1.9 %) |
| 09_demo_storyline | 434 | ✅ | 0.882 | 0.234 | 0.927 | 9/305 (3.0 %) |

"Calm" = scenario voice level < 0.3, "stressed" = ≥ 0.5. r is low in 01, 06 and 07 because the voice level barely changes in those scenarios (nothing to track), not because scoring fails. Single-utterance false alarms of 1–5 % are why fusion should look at several utterances and other sensors, not one clip.

## 3. Cabin-noise robustness (`robustness.py --n 20`)
Fan hum (60 Hz + harmonics) + pink noise, 4 synthetic speakers × 20 utterances per condition (80 calm + 80 fully aroused). Baselines enrolled at 20 dB SNR. Results: `results/robustness.json`.

| Pipeline | SNR dB | Calm ≥ 0.6 (false alarm) | Aroused ≥ 0.6 (detected) | Mean score calm | Mean score aroused | Feature drift (SD) |
|---|---|---|---|---|---|---|
| no_filter | 30 | 0.0 % | 100.0 % | 0.170 | 0.987 | 0.849 |
| no_filter | 20 | 0.0 % | 100.0 % | 0.180 | 0.986 | 0.638 |
| no_filter | 10 | 5.0 % | 100.0 % | 0.312 | 0.985 | 1.400 |
| no_filter | 5 | 3.7 % | 98.8 % | 0.370 | 0.947 | 2.169 |
| no_filter | 0 | 2.5 % | **48.7 %** | 0.264 | 0.438 | 3.069 |
| bandpass | 30 | 0.0 % | 100.0 % | 0.134 | 0.976 | 0.808 |
| bandpass | 20 | 0.0 % | 100.0 % | 0.178 | 0.983 | 0.681 |
| bandpass | 10 | 8.7 % | 100.0 % | 0.365 | 0.989 | 1.408 |
| bandpass | 5 | 16.3 % | 100.0 % | 0.472 | 0.992 | 1.757 |
| bandpass | 0 | **37.5 %** | 100.0 % | 0.582 | 0.994 | 2.138 |
| **bandpass+denoise (default)** | 30 | 0.0 % | 100.0 % | 0.143 | 0.978 | 0.790 |
| **bandpass+denoise (default)** | 20 | 0.0 % | 100.0 % | 0.178 | 0.983 | 0.682 |
| **bandpass+denoise (default)** | 10 | 6.2 % | 100.0 % | 0.346 | 0.988 | 1.423 |
| **bandpass+denoise (default)** | 5 | 11.3 % | 100.0 % | 0.419 | 0.991 | 1.769 |
| **bandpass+denoise (default)** | 0 | 16.3 % | 100.0 % | 0.458 | 0.992 | 2.034 |

**Reading:**
- Without the filter, loud fan hum **hides** stress: at 0 dB only 48.7 % of aroused speech is detected (hum dominates and pulls spectral features down).
- The band-pass keeps detection at 100 %, but on its own it raises false alarms in heavy noise (37.5 % at 0 dB), because broadband noise left in the speech band looks like extra vocal effort.
- Subtracting the noise measured in speech pauses (our default) cuts that to 16.3 % at 0 dB while keeping 100 % detection.
- Remaining weakness: at ≤ 5 dB SNR, 11–16 % of calm utterances still score ≥ 0.6. The confidence heuristic halves confidence below 5 dB, so fusion down-weights these.

## 4. Not done yet (needs data we could not download in this session)
- **RAVDESS** training/evaluation (`train.py`): would give balanced accuracy on unseen actors, for acted arousal. Report rule score and logistic regression side by side, mean ± SD and worst fold.
- **Artemis II** demo (`artemis_demo.py`): feature traces and filter spectrogram on real crew audio. Demonstration only.

Until those are run, the only valid voice claims are the ones in sections 1–3, stated as synthetic.


## AST-05 roster fix (2026-11-15)

Direct Python integration check passed on all five synthetic profiles: 10 calm enrollment clips per speaker; each yielded a six-field voice record with the correct crew ID and 10-clip personal baseline. All five baseline objects were distinct. AST-06 returned `invalid_input`. For AST-05, four additional calm clips averaged 0.22475 and four synthetic aroused clips averaged 0.987; all aroused scores exceeded calm scores. This verifies software behavior on synthetic audio, not accuracy on real speech.

The existing pytest suite has a new AST-05 case and the output count expectation is now five. The suite was not run in this environment: pytest is unavailable and installation could not reach PyPI (DNS blocked). No dependencies were added to the repository.
