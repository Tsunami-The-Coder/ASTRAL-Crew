# models/voice/: voice stress indicator (owner: Ben)

Part of **ASTRAL-Crew** (NASA Space Apps 2026, *Create Health Monitoring Software for Astronauts on Space Missions*). This module listens to an astronaut's comms speech and reports how far their voice has moved from **their own calm baseline**, in the directions linked to stress. Fusion combines it with Khalid's wearable output.

> Research indicator, not a diagnosis. Runs fully offline (numpy + scipy).

The crew roster accepts `AST-01` through `AST-05`. Each speaker requires their
own calm enrollment; `synth.py` includes a fifth synthetic test profile.

## How it works
```
comms audio ──► 300–3400 Hz Butterworth band-pass ──► voice activity detection
           ──► noise estimate from pauses (spectral subtraction)
           ──► features: pitch, jitter, loudness, shimmer, spectral tilt,
                         Teager energy (TEO), TEO-CB-Auto-Env, MFCC
           ──► z-scores vs. this astronaut's calm baseline (Digital Twin)
           ──► stress_score 0–1 + confidence + explanation
           ──► {"crew_id","timestamp","stress_score","confidence","source":"voice","data_type"}
```
Why a personal baseline: we have no labelled astronaut stress speech, and voices differ a lot between people (a calm 205 Hz voice is not "stressed" just because it is higher than a 115 Hz voice). See `research/SCIENCE_REVIEW.md` item 1.

## Quick start (from repo root)
```bash
pip install numpy scipy pandas scikit-learn pytest      # nothing new for the team
python -m pytest models/voice -q                        # 28 tests, ~15 s
python -m models.voice.demo                             # real pipeline on scenario 09 (synthetic audio)
python -m models.voice.demo --all                       # all 9 scenarios -> data/processed/voice_outputs/
python -m models.voice.robustness --n 10                # cabin-noise test, ~1 min
```
Real audio:
```bash
python -m models.voice.cli enroll  AST-01 calm1.wav calm2.wav calm3.wav calm4.wav calm5.wav
python -m models.voice.cli analyze AST-01 new_clip.wav --timestamp 2026-11-14T09:15:00Z
python -m models.voice.artemis_demo --in data/raw/audio/artemis2   # NASA audio demo (no stress claims)
```
Optional training (after downloading RAVDESS, see `train.py`):
```bash
python -m data.scripts.ravdess_prepare --in data/raw/RAVDESS
python -m models.voice.train          # writes results/ravdess_eval.json and model.json
```

## Files
| File | Contents |
|---|---|
| `__init__.py` | Public API: `VoiceStressEstimator`, `VoiceResult`, `make_record`, `CONTRACT_KEYS` |
| `features.py` | Band-pass, VAD, spectral subtraction, MFCC, pitch, TEO, utterance features |
| `baseline.py` | Personal calm-voice baseline per astronaut, saved as JSON |
| `scoring.py` | Baseline z-scores → stress_score, confidence, explanation; optional model |
| `inference.py` | `VoiceStressEstimator` (enroll / analyze) |
| `cli.py` | Command line: `python -m models.voice.cli enroll / analyze / analyze-dir` |
| `train.py` | Optional RAVDESS training with actor-independent folds |
| `synth.py` | **Synthetic** speech-like audio and cabin noise for tests/demos |
| `demo.py` | Runs the real pipeline on Eleni's 9 scenarios → contract JSONL for fusion |
| `robustness.py` | Cabin-noise test: no filter vs. band-pass vs. band-pass + denoise |
| `artemis_demo.py` | Feature demo on real NASA Artemis II audio + filter spectrogram |
| `test_voice.py` | 28 tests: signal processing, contract, invalid input, baseline, scripts |
| `results/robustness.json` | Output of `robustness.py` (synthetic) |
| `MODEL_CARD.md` | Purpose, method, assumptions, limitations |
| `VALIDATION.md` | What was actually measured, with numbers |
| `CONTRACT_PROPOSAL.md` | Voice section for `docs/DATA_CONTRACT.md` |
| `COLIN_HANDOFF.md` | How fusion uses this module |
| `SOURCES.md` | References, datasets, licences, AI disclosure |
| `requirements-voice.txt` | Dependencies (no new ones) |

## Honest wording for the pitch
| Avoid | Say |
|---|---|
| "Detects stress from voice with X % accuracy" | "Flags deviation from each astronaut's own calm voice; tested on synthetic speech and cabin noise" |
| "Validated on NASA audio" | "Demonstrated on authentic Artemis II crew audio" |
| "Uses SUSAS" | "Feature design grounded in SUSAS research (Hansen et al.)" |

