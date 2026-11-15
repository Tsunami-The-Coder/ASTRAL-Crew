# Integration — fusion and QA (backend lead)

Planned: voice/wearable signal fusion, missing-signal handling, crew-level environmental correlations, scenario tests.

Treat outputs as decision support, not diagnoses.

Restored integration prototype is implemented in `adapters.py`, `rules.py`,
and `demo.py`; see [INTEGRATION.md](INTEGRATION.md) for assumptions and review
questions. `backend/multimodal.py` composes these outputs with existing telemetry
rules and preserves compatibility with mission-log storage. It is not an approved
shared contract or a calibrated/clinical fusion model. Actual producer functions
were tested together in a temporary copy on synthetic waveforms; model files and
shared config remain unchanged on this branch.
