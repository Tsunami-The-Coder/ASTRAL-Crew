# Multimodal integration prototype — pending team review

Backend/fusion owner: Aarika (Colin unavailable). No shared contract, model source,
root dependency file, UI file, or Git history is modified by this implementation.
This is an internal candidate adapter, not a declaration that either owner's
proposal has been approved. Review these assumptions with Ben, Khalid, and Anuj.

## Architecture

```
Ben's actual VoiceResult + explicit audio window end/version/provenance
                         -> adapt_voice -------------------------\
                                                                  compare_modalities
Khalid's actual assess output -> adapt_wearable ------------------/        |
                                                                           |
Synthetic cabin/crew snapshot + reference -> existing backend rules --------+
                                                                           |
                                                    analyze_multimodal report
                                                                           |
                                                    MissionLog -> MissionService
```

No model is trained here. No two uncalibrated scores are averaged. Both original
JSON-safe outputs, source semantics, quality, versions and limitations survive
in the report. Non-JSON producer payloads are rejected with an explicit issue;
they cannot be faithfully logged as strict JSON and their raw capture is omitted.
Numeric invalid input never becomes a normal/zero score.

## Explicit adapter decisions

- Voice record timestamp is utterance START. The caller supplies the actual end
  using the audio duration, not an invented 60-second window. It also supplies
  the actual method/artifact version; a learned voice artifact must be identified
  separately from the default personal-baseline method.
- Voice data_type=real is ambiguous. Caller must choose measured, research, or
  replayed provenance; no automatic reinterpretation of a research clip as live
  measured audio. The original data_type is retained in raw.record.
- Wearable timestamp is observation END, with explicit window_start. The adapter
  accepts wearable-proposal-v1, preserves null confidence, and retains its
  score_semantics and inference_origin. It never fabricates feature extraction
  provenance or motion to make missing backend features pass the research model.
- Missing/no_speech/enrollment/invalid/model_unavailable/stale are visible states.
  No valid voice record is expected during silence. An unavailable model is not
  a low score. A non-JSON payload is explicitly invalid.
- Before combining evidence, check crew/source, explicit time windows, freshness,
  overlapping windows, and matching input provenance. Input provenance must also
  match the synthetic snapshot used by this internal backend.
- Recheck freshness at comparison time, even for cached normalized evidence.
  The pure wrapper requires snapshot_timestamp and now; default maximum age is
  300s and allowed end-time difference from the snapshot is 60s. These are demo
  settings, not an agreed production clock policy. Replay supplies a scenario clock.
- Voice confidence below 0.5 and wearable motion_caution withhold paired
  interpretation; original evidence remains visible. These are prototype rules.
- Per-modality low/elevated bands are independently configurable (defaults
  0.4/0.6 for each), **unvalidated engineering choices**, not calibrated risk
  equivalence or medical thresholds. Intermediate scores remain inconclusive.
- Possible findings: BOTH_INDICATORS_ELEVATED, MODALITY_DISAGREEMENT,
  MOVEMENT_CAUTION. Disagreement does not establish hardware failure; calm speech
  cannot exclude physiological illness. No psychological/contagion diagnosis,
  clinical RED state, task reassignment, lockout, or spacecraft control exists.
- Current producers support AST-01..AST-04. Backend still supports five; AST-05
  model results stay unsupported/unavailable. Do not clone another person's score.

## Existing APIs and provenance

Checked producer versions from fetched source:

- Voice: feature/voice-ai at c6caec4267f56a6adb1a20fc6eb4fa076eb7f56e.
- Wearable: main at b61174e32cebe1ffe4a91fb80eaf3d32efd0f16d; wearable artifact
  wesad-wrist-logistic-v1. Its documented pulse-detector limitation still applies.

These sources were staged into a disposable integration environment for testing;
they were not copied into or merged with the backend branch. Shared interfaces
still need agreement and cross-owner review. Raw independent research datasets
must not be described as naturally synchronized voice/wearable observations.

## Offline synthetic integration demonstration

Once BOTH owners' modules are available together, install their documented
runtime dependencies in your chosen environment, then run from the project root:

```sh
python3 -m fusion.demo --database /tmp/astral-real-fusion-demo.sqlite3 --model-path models/wearable/model.json --crew-count 4
```

Use a new database filename each run. Requires numpy/scipy and both model modules.
The CLI explicitly errors when they are absent; it does not download or train.
`--crew-count 5` demonstrates unsupported fifth-person inputs without inventing
scores. It does not change the team's agreed roster. The scenario clock is pinned
and labeled synthetic. The service uses that clock to inspect the replay.

This demo runs Ben's synthetic speaker/audio generation and actual baseline
inference; Khalid's actual feature extraction on generated 60-second BVP/EDA/ACC
arrays and actual research-model inference; then both adapters, cross-analysis,
SQLite logging, a **synthetic** review entry, and service retrieval. Wearable
features in the current backend snapshot are replaced by the actually extracted
synthetic summaries so raw observations and model input agree. No human data is
processed. A synthetic review is never portrayed as an actual crew review.

For external input, call adapters with real window/version/provenance metadata,
then analyze_multimodal(snapshot, profiles, snapshot_timestamp=..., now=...,
voice_by_crew=..., wearable_by_crew=..., previous=...). The returned report is
compatible with existing MissionLog.save_analysis; it does not save itself.
Timestamp/source-ID consistency is the caller's responsibility at persistence.
The existing snapshot voice fields are unchanged, and standalone cross_analysis
CLI continues to run telemetry-only rules. Use the new wrapper/demo for models.

## Review questions before shared integration

1. Agree on four/five crew for the final demonstration.
2. Approve input-origin mapping, voice duration metadata and exact model versions.
3. Approve per-signal freshness, window-overlap and snapshot alignment policy.
4. Review band/caution choices and UI wording; calibration remains unestablished.
5. Choose an integrated application path: Python service or separate browser
   prototype. This change does not connect browser-local storage to SQLite.
6. Add the agreed adapter schema to shared documentation and producer/consumer
   fixtures together, rather than declaring either current proposal authoritative.
