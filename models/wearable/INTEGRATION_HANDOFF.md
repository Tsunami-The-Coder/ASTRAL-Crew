# Wearable handoff to the integration lead

Task / owner: issue #4, wearable owner. Branch: feature/wearable-fixes.
Scope: models/wearable only. Shared contract remains a proposal.

## NASA resource review follow-up

Read `NASA_WEARABLE_REVIEW.md` for source-to-feature decisions and data-access
findings. `space_scenarios.py` provides nine wearable-only software scenarios.
Rebuild stored baselines with `build_baseline`: matching `feature_pipeline` and
`window_seconds` are now required to display personal deltas. Source lists have
expanded; iterate over them. No new runtime dependencies or shared event fields.

The raw-signal audit found v1 double-counting secondary waveform peaks. Keep its
predictions labelled experimental; do not present the WESAD classification metric
as evidence of accurate HRV, spaceflight validity or five-hazard diagnosis.
`signal_audit.py` reproduces the issue. See FIX_VALIDATION.md for the new quality-gated model and evaluation.

## Connect the component

1. Import `assess` and `load_model` from `models.wearable`.
2. Supply the approved backend summary plus the actual window start/end,
   crew ID, input provenance and feature-pipeline ID. Do not manufacture missing
   timing or label ECG measurements as wrist BVP features.
3. Load the included `models/wearable/model.json` once; inject it into `assess`.
   No retraining is required. Resolve the path from your application location.
   If it is absent, preserve `model_unavailable` and the null score.
4. Match voice and wearable observations by crew and overlapping intervals.
   Require a team-agreed freshness policy; do not match merely because two
   records occupy the same row in unrelated datasets.
5. Keep modality results and quality distinct. `confidence=null` is intentional.
   Do not multiply a score by a made-up confidence or average uncalibrated scores.
6. Build a fusion result that exposes agreement, disagreement, single-modality
   availability or insufficient information. Use explicit rules reviewed by the team.
7. Pass that assessment via the backend lead's backend to the UI lead's UI/log, preserving
   provenance, reasons, time window and source references.

The current implementation contains no changes to your fusion code. Your actual
function signatures were not available in the inspected planning repository.
The synthetic voice fixture is not a claim about the voice lead's output schema.

## Suggested adapter decisions (assumptions, not approved behavior)

| Situation | Proposed handling |
|---|---|
| Both modalities usable | Show both with agreement/disagreement; numerical fusion requires calibration |
| Wearable missing/invalid/stale | Exclude its score; retain a visible status |
| Voice absent | Wearable-only result, explicitly partial |
| Different crew IDs | Do not combine |
| Non-overlapping windows | Do not combine; wait or display separate observations |
| High motion | Retain caution; do not equate physiological activation with psychological stress |
| Multiple crew changes + CO2 increase | Flag possible shared context for human investigation; no causal claim |
| No models | Display observations/quality, no fabricated stress assessment |

For schema differences, agree a minimal adapter at the handoff. Update the shared
contract, producer/consumer fixtures and integration tests together after review.
Do not silently rename `data_origin` to the playbook's earlier `data_type`.

## Acceptance checks for the integrated app

- Five distinct crew records reach the correct cards.
- Window timestamps and units survive backend serialization and storage.
- Missing EDA yields unavailable wearable inference, not a normal score.
- Stale signals are excluded even if their previous score was high/low.
- Sensor disagreement is visible with both source results.
- An unavailable model does not crash the dashboard.
- Each chart/report retains synthetic/replayed/research origin labels.
- Crew-wide/environment associations are phrased as hypotheses.
- User-reviewed next steps and any simulated action are logged separately.
- App still works offline using synthetic fixtures.

Run component tests and demo from README.md. Actual results are in VALIDATION.md.
Optional training dependencies are local to this folder; runtime inference uses
the Python standard library. No root dependency/config file was edited.

## Ready-to-send message (not sent automatically)

Integration team - the wearable component is ready for interface review on
`feature/wearable-ai` under `models/wearable/`.

It supplies window-based wearable results with crew ID, timestamps, score meaning,
data origin, model version, quality, limitations and NASA evidence references.
The contract is a proposal; please review `CONTRACT_PROPOSAL.md` before wiring it in.

You can call `assess(event, model=model)` and pass an explicit scenario clock for
replay. Missing/invalid/stale signals and unavailable models return null scores.
Please preserve those states. The default demo uses hand-authored synthetic
fixtures; the included WESAD-trained `model.json` can be injected without retraining. All demo telemetry
remains synthetic. The research model expects the documented wrist feature pipeline.

My integration assumptions: align by crew and observation window, show modality
disagreement, and avoid averaging scores until their calibration/meaning is agreed.
Shared crew changes plus environmental telemetry should trigger investigation,
not a diagnosis or autonomous intervention.

If your interface differs, let's agree a small adapter and update the shared
contract and integration tests together. `demo.py` includes five scenarios with
25 crew results; `VALIDATION.md` records the actual component/model checks.
NASA source mappings, limitations and AI/data provenance are documented alongside.

Current model: wesad-wrist-logistic-v2-quality-gated. The shared field names and accepted-feature definitions are unchanged. Review FIX_VALIDATION.md: only four held-out participants retain both classes, and raw-data coverage is limited. Do not reuse the historical 85.5% claim or assume the dashboard's separately copied model has been updated.
