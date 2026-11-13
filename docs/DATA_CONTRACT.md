# Proposed integration contract (planning)

This is a *schema proposal*, not an implemented data pipeline. Confirm units and field names as a team before coding.

## Telemetry event
```json
{
  "timestamp": "2026-11-14T14:30:00Z",
  "mission_day": 142,
  "crew_id": "AST-02",
  "data_origin": "synthetic",
  "biometrics": {
    "heart_rate_bpm": 92,
    "hrv_rmssd_ms": 28,
    "eda_microsiemens": 5.2,
    "motion_level": 0.15
  },
  "voice": {
    "stress_score": 0.78,
    "model_version": "demo-v1",
    "data_origin": "simulated_inference"
  },
  "environment": {
    "co2_percent": 0.32,
    "o2_percent": 21.0,
    "pressure_kpa": 101.0
  },
  "assessment": {
    "stress_state": "AMBER",
    "needs_review": true
  }
}
```

## Model handoffs
- Voice and biometric outputs must each identify model version, source, timestamp, score/label, and limitations.
- Fusion must distinguish *missing signal* from *normal signal*.
- Correlation findings should be phrased as hypotheses, not diagnoses.
- All proposed spacecraft interventions are simulated and human-reviewed.
