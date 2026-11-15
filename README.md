# ASTRAL-Crew 🚀
**Autonomous Spaceflight Health & Crew Resilience** — NASA Space Apps Challenge 2026

Offline-first, software-only prototype for a four-person Mars mission. Combines recorded research signals, synthetic spacecraft telemetry, and human-reviewed decision support.

> **Planning stage:** Implement code only after the official hackathon start. Demo data and autonomous actions are simulated. Not a medical device.

## Planned screens
1. Mission Control — four astronaut cards, cabin readings, alerts
2. Crew Health Twins — baselines, trends, interactive body map
3. Cognitive AI — voice and wearable stress indicators
4. Five Hazards — radiation, gravity, habitat, medical, cognitive
5. Crew Diagnostics — cross-crew patterns and sensor verification
6. Mission Logs — offline incident history and exports

## Team
| Member | Responsibility |
|---|---|
| UI lead | UI/UX and product integration |
| backend lead | Backend, SQLite, simulation |
| research lead | Research, datasets and scientific citations |
| wearable lead | Wearable biometric AI |
| voice lead | Voice AI |
| integration lead | Multimodal fusion, anomaly rules, QA |

## Planned stack
Python, Streamlit, Plotly, pandas, SciPy, librosa, XGBoost, SQLite.

## Start here
- [Contribution workflow](CONTRIBUTING.md)
- [Team plan](docs/TEAM_PLAN.md)
- [Data sources and access checks](docs/DATA_SOURCES.md)
- [Shared data contract](docs/DATA_CONTRACT.md)
- [GitHub Issues](../../issues) for individual workstreams

## Timeline
- **Nov 13:** Planning, coordination, dataset verification, wireframes
- **Nov 14:** Implementation after the official event start; integrate early
- **Nov 15:** Testing, demo, citations, submission

## Research integrity
WESAD and speech recordings are research datasets, not validated astronaut medical monitoring. Independent audio and wearable sources are not naturally synchronized. Distinguish measured, replayed and synthetic data. Avoid diagnostic claims; safety-critical actions remain human-reviewed.
