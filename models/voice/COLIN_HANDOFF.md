# Handoff to Colin (fusion): voice stress component

## TL;DR
- **Drop-in data now:** `python -m models.voice.demo --all` writes `data/processed/voice_outputs/<scenario>.jsonl` for all nine scenarios. These are produced by the **real** voice pipeline (on synthetic audio), in exactly the contract format. Use them instead of the voice lines in `mock_model_outputs.jsonl`.
- **Live API:**
```python
from models.voice import VoiceStressEstimator

est = VoiceStressEstimator(baseline_path="data/processed/voice_baselines.json")
res = est.analyze(audio_float32_mono, crew_id="AST-01", timestamp="2026-11-14T09:15:00Z", sr=16000)
if res.ok:
    fusion_input.append(res.record)     # 6 contract keys
else:
    pass                                # voice missing: res.details["status"] says why
```
- **Missing voice is normal.** No record when nobody speaks, while a baseline is being enrolled, or on bad input. `analyze()` never raises on bad audio.

## Interface (stable)
| Name | What |
|---|---|
| `VoiceStressEstimator(baseline_path=None, model_path=<model.json>, min_enroll=5, auto_enroll=True)` | `baseline_path=None` keeps baselines in memory (good for tests) |
| `.enroll(crew_id, clips, sr=16000, data_type="real", replace=False)` | clips = arrays or WAV paths of calm speech |
| `.analyze(audio, crew_id, timestamp=None, sr=16000, data_type="real") -> VoiceResult` | |
| `.analyze_file(path, crew_id, timestamp=None, data_type="real") -> VoiceResult` | |
| `VoiceResult.record` / `.details` / `.ok` | record is `None` or the 6-key dict |
| `make_record(...)`, `CONTRACT_KEYS`, `write_jsonl(records, path)` | helpers |

## How to read the numbers
- `stress_score` ≈ 0.15–0.30 for calm speech against the person's own baseline, ≥ 0.6 clearly elevated (on our synthetic checks: calm mean 0.22–0.27, stressed mean 0.84–0.99 across scenarios).
- Weight by `confidence`. It drops with noise (< 12 dB SNR × 0.75, < 5 dB × 0.5), short speech and small baselines.
- At very low SNR (≤ 5 dB) the false-alarm rate on calm synthetic speech rises to 11–16 %; that is why confidence is lowered there.

## Suggested fusion uses
1. **Sensor fault (scenario 06):** HR > 200 at low motion **and** voice `stress_score < 0.4` with `confidence ≥ 0.5` → likely wearable fault.
2. **Exercise (07):** voice stays calm during exercise in our scenarios. Breathless speech after exercise can raise loudness and pitch, so prefer the accelerometer there.
3. **Contagion (05, 09):** voice onsets can confirm the order of onsets seen in the wearable (origin → next crew member).
4. **Never alone:** do not raise RED from voice alone.

## Checks I ran (see VALIDATION.md)
- `python -m pytest models/voice -q`: 28 passed (includes Eleni's `check_outputs` on my records).
- Ran together with Eleni's tests: `python -m pytest tests models/voice -q`: 48 passed.
- All nine scenario outputs pass `check_outputs`.

## Assumptions to confirm with you
- Calm threshold 0.4 / elevated 0.6 are suggestions, not fitted values.
- `crew_id` comes from the comms channel (headset ID), so the speaker is known. If that's not true, we need speaker identification first.
