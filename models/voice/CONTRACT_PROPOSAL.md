# Voice section for `docs/DATA_CONTRACT.md` (proposal from Ben)

Fully compatible with the playbook example and with Eleni's `research/DATA_CONTRACT_PROPOSAL.md`. Nothing new is required from other workstreams.

## Record (voice → fusion), unchanged schema
```json
{"crew_id": "AST-01", "timestamp": "2026-11-14T09:15:00Z", "stress_score": 0.41,
 "confidence": 0.78, "source": "voice", "data_type": "real"}
```
| Field | Type | Meaning |
|---|---|---|
| `crew_id` | `AST-01`…`AST-05` | Speaker. Must be the person actually talking (the baseline is per person). |
| `timestamp` | ISO-8601 UTC with `Z` | Start of the utterance |
| `stress_score` | float 0–1, 3 decimals | Vocal arousal relative to **personal** calm baseline. ~0.15–0.3 = typical calm, ≥ 0.6 = clearly elevated. Not clinical. |
| `confidence` | float 0.05–0.95 | Heuristic trust in this record (speech length, SNR, clipping, baseline size). Not a calibrated probability. |
| `source` | `"voice"` | Always |
| `data_type` | `"real"` \| `"synthetic"` | Passed through from the caller |

Records contain **exactly** these six keys, so Eleni's `validate_data.check_outputs` accepts them.

## When there is NO record
Voice records only exist when the astronaut speaks (Eleni's contract rule). `VoiceStressEstimator.analyze()` returns `record=None` and a `details["status"]`:
| `status` | Meaning | Fusion should |
|---|---|---|
| `no_speech` | Silence, noise only, or < 1 s of speech | Treat voice as missing |
| `enrolling_baseline` | Fewer than 5 calm utterances stored for this person | Treat voice as missing |
| `invalid_input` | Unknown `crew_id`, bad timestamp, unreadable/NaN audio | Treat voice as missing; log `reason` |

## Optional `details` (not part of the record)
Kept separate so the contract does not change. Useful for the UI ("why?") and the mission log:
```json
{"status": "ok", "method": "personal_baseline_v1", "baseline_n": 10, "model_used": false,
 "rule_score": 0.41, "arousal_deviation_sd": 0.78, "profile_distance": 0.66,
 "flags": ["moderate_noise"],
 "top_contributors": [{"feature": "f0_mean_hz", "label": "pitch", "z": 2.1, "contribution": 2.1}],
 "explanation": "Vocal arousal mildly above personal baseline (pitch 2.1 SD above own baseline). Research indicator, not a diagnosis.",
 "quality": {"speech_s": 2.4, "snr_db": 11.2, "clipped": false, ...},
 "features": {"f0_mean_hz": 131.2, ...}}
```
Possible `flags`: `short_utterance`, `low_snr`, `moderate_noise`, `clipping`, `small_baseline`, `voice_profile_mismatch`.

## Open questions for Colin
1. Sensor-fault rule from the pitch: "wearable says 220 bpm, voice is calm". Voice is "calm" when `stress_score < 0.4` with `confidence ≥ 0.5`. OK?
2. Should `details.flags` travel with the record into fusion (e.g. as an optional `"quality"` key, like Eleni suggested for the wearable)? That would need everyone to agree to an optional key, and Eleni's validator would need to allow it.

