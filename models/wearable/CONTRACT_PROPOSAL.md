# Wearable-owned handoff proposal v1

**Status: implemented locally for review, not a team-approved shared contract.**
Owner: Khalid. Next integration owner: Colin; backend: Aarika; display: Anuj.
No edits to the shared contract or another workstream are included.

## Input

`assess(event, model=None, baseline=None, now=None, max_age_seconds=300)` accepts
one summary of one crew member's observation window. Existing telemetry fields
retain their names. Extra telemetry fields are not modified.

| Field | Meaning |
|---|---|
| crew_id | AST-01 through AST-04 |
| timestamp | Window END, ISO 8601 with timezone; normalized to UTC |
| window_start | Proposed explicit beginning; 60..300 seconds before end |
| data_origin | synthetic, research, replayed, or measured; required |
| feature_pipeline | Required match to research model extraction method |
| biometrics.heart_rate_bpm | Mean heart/pulse rate, beats/min |
| biometrics.hrv_rmssd_ms | RMSSD, milliseconds; wrist model uses pulse-derived proxy |
| biometrics.eda_microsiemens | Mean skin conductance, microsiemens |
| biometrics.motion_level | Proposed normalized motion, 0..1; mapping below |
| context.sleep_hours | Optional 0..24, context only |
| context.self_report_stress_0_10 | Optional 0..10, context only |

The raw wrist pipeline `wrist-bvp-eda-acc-60s-v1` uses exactly 60-second windows,
bandpassed BVP pulse peaks, valid consecutive intervals, mean EDA, and
`motion_level=min(dynamic_acceleration_rms_g/0.2, 1)`.
Dynamic acceleration removes the per-axis window mean. The 0.2 g divisor is
an explicit engineering assumption, not a NASA threshold. The original E4 ACC
units are converted to g by dividing by 64. Do not label a different scaling
or ECG-based extraction with this pipeline ID.

The shared telemetry example supplies a scalar HRV, EDA and motion level but
does not define their window or extraction method. An adapter must obtain these
facts from the producer; it must not invent them. Missing `window_start` fails
validation. The 60..300s summary envelope allows a future extraction version;
the current research model only accepts its 60s feature pipeline.

## Output

- `schema_version`: wearable-proposal-v1; `source`: wearable.
- `crew_id`, `timestamp`, `window_start`: identity and observation interval.
- `data_origin`: provenance of INPUT; never overwritten by model provenance.
- `inference_origin`: simulated_inference or research_model_inference when scored.
- `status`: available, missing, invalid, stale, model_unavailable, model_invalid,
  or incompatible_features.
- `stress_score`: number 0..1 only when available; otherwise null.
- `score_semantics`: synthetic_demo_score OR uncalibrated_WESAD_stress_class_probability.
- `confidence`: always null; no calibration or clinical certainty established.
- `model_version`: explicit when scored.
- `feature_pipeline`: preserves the supplied extraction identifier or null.
- `quality`: summary usability and issues, separate from score.
- `observations`: measured summaries; baseline medians and absolute deltas when valid.
- `baseline`: available/unavailable/invalid, reference date and provenance where valid.
- `context`: valid optional self-report/sleep information; never added to model inputs.
- `evidence_ids`: resolve using SOURCES.md.
- `evidence`: offline title, URL and design-use metadata for those references.
- `explanation`: readable observations, availability and limitations for UI display.
- `limitations`, `ai_assisted`: visible throughout downstream UI and export.

Normal-looking observations do not mean a medical 'normal' status. Availability
is not a diagnosis. Numeric validation bounds are broad engineering checks:
heart rate 20..240, RMSSD 0..500, EDA 0..100, motion 0..1. They are not treatment
or alert boundaries and must not be presented as NASA clinical standards.

## Time and missing-data behavior

Default `now` is real UTC; future windows are invalid, windows older than
300s are stale. Replay must explicitly pass a scenario clock and preserve
`data_origin=replayed` or `synthetic`. Production freshness/clock tolerances need
team agreement. Invalid fields dominate missing fields. Neither becomes score zero.

`build_baseline` requires >=5 distinct non-overlapping, valid, low-motion windows
from one person and one provenance category. The caller chooses a suitable
calibration period; the algorithm does not infer that someone was healthy.
All reference windows must also share one explicit `feature_pipeline` and one
duration in 60..300 seconds. The returned baseline stores `feature_pipeline` and
`window_seconds`; both must match the current event. Rebuild cached baselines
created before these fields were added. Incompatible references produce no deltas
and do not change the current stress score. This is wearable-owned proposal metadata.
The baseline must end before the scored window. Baseline deltas are observations,
not extra training features or a calibrated personal risk score.

## Decisions requested in review

1. Confirm window semantics, optional context fields and upstream feature mapping.
2. Agree on origin vocabulary and the distinction between input/model origins.
3. Confirm null-score and status handling in fusion/backend/UI.
4. Choose temporal overlap/freshness rules for real integration.
5. Define how different modality scores will be calibrated before numerical fusion.

Until then, examples are fixtures for discussion. They do not establish a shared API.
