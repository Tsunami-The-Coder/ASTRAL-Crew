# Wearable stress research prototype - Khalid

Offline component for ASTRAL-Crew. AI-assisted code and synthetic fixtures.
No medical diagnosis, astronaut validation, or autonomous spacecraft control.

**Signal audit finding:** v1 can mistake secondary waveform peaks for pulses.
The included model remains an experimental baseline. See
[NASA_WEARABLE_REVIEW.md](NASA_WEARABLE_REVIEW.md) for the reproduced limitation,
challenge-source mapping, data-access findings and five-hazard scope.

## What works

- Consume window summaries using the existing telemetry biometric names.
- Validate identity, time window, units/ranges, freshness, and data origin.
- Return missing/invalid/stale/model-unavailable explicitly, with a null score.
- Compare readings to a separate, earlier, same-person calibration baseline.
- Run inert JSON logistic models without third-party runtime dependencies.
- Extract 60-second WESAD wrist features and train a participant-independent baseline.
- Demonstrate four crew members across five synthetic scenarios.
- Trace NASA design evidence through [SOURCES.md](SOURCES.md).

The handoff in [CONTRACT_PROPOSAL.md](CONTRACT_PROPOSAL.md) is **proposed**.
It does not amend `docs/DATA_CONTRACT.md`. Shared integration requires team review.
Inspect [example.json](example.json) for a synthetic input/output pair.
See [COLIN_HANDOFF.md](COLIN_HANDOFF.md) for integration and a ready-to-send message.

## Run locally

Use Python 3.11+ from the repository root. These are Python execution steps,
not Git commands; commits and PRs follow the team's GitHub website workflow.

```text
python -m unittest models.wearable.test_wearable -v
python -m unittest models.wearable.test_space -v
python -m models.wearable.demo --output ../wearable-demo
python -m models.wearable.space_scenarios --output ../wearable-space-scenarios.json
```

Open `wearable-demo.html` for the readable engineering report, or use
`wearable-demo.json` as integration fixtures. The default model is a deliberately
hand-authored **synthetic fixture**, not a trained/validated predictor.
Training tests skip if optional dependencies are absent; the test summary reports this.

The nine wearable-only space scenarios are software checks with arbitrary synthetic
values, not training examples or a space physiology simulator. With optional training
dependencies installed, reproduce the peak-detector audit using:

```text
python -m models.wearable.signal_audit --output ../wearable-signal-audit.json
```

## Use the included trained model

`model.json` contains the WESAD-trained research model. No download or retraining
is required for inference. Run from the repository root:

```text
python -m models.wearable.demo --model models/wearable/model.json --output ../wearable-research-demo
```

Demo inputs remain synthetic. The model is uncalibrated and not validated for
astronauts or clinical use. See SOURCES.md for WESAD attribution and use conditions.

## Train on the original WESAD data (optional)

1. Read the original scientific/non-commercial use terms linked in SOURCES.md.
2. Download the original WESAD.zip from the University of Siegen source.
3. Keep the raw archive and new training outputs outside the repository. The reviewed research model is included as `models/wearable/model.json`.
4. Install optional dependencies and run:

```text
python -m pip install -r models/wearable/requirements-training.txt
python -m models.wearable.train /path/to/WESAD.zip --output /outside/repo/wearable-run --trusted-original-wesad
python -m models.wearable.demo --model /outside/repo/wearable-run/model.json --output /outside/repo/wearable-demo
```

The training command reads pickle from the original archive. Pickle is executable:
do not supply an untrusted archive. The flag records an explicit source check;
it is not a cryptographic authenticity guarantee.

Outputs: `model.json` and `evaluation.json`. No raw participant features are exported.
The model refitted on all subjects is distinct from the held-out fold models used
to measure performance. Synthetic demo data remain synthetic when using a research model.

## Minimal Python integration

```python
from models.wearable import assess, load_model

model = load_model("models/wearable/model.json")
result = assess(window_event, model=model)  # real UTC freshness checks
```

For reproducible replay, supply the explicit scenario clock through `now=`.
Inputs must include `window_start`, `timestamp`, `crew_id`, `data_origin`,
`feature_pipeline` and `biometrics`; see the contract proposal.
No package import downloads data or starts training.

## Verification and limitations

See [VALIDATION.md](VALIDATION.md) for actual run evidence and
[MODEL_CARD.md](MODEL_CARD.md) for intended use, feature semantics and evaluation.
This component has not been connected to the other workstreams: their inspected
branches contain plans, and our proposal has not been approved by their owners.
