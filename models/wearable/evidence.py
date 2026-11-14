"""Paraphrased design evidence and non-clinical review prompts; AI-assisted.

These references motivate the design. They do not endorse model outputs or
provide numerical parameters. EDA model evidence comes from WESAD, not NASA.
"""
REFERENCES = {
    "NASA-HAZARDS": {
        "title": "Five Hazards of Human Spaceflight",
        "url": "https://www.nasa.gov/hrp/hazards/",
        "use": "Scope and transfer limits; the hazards are not five wrist-derived diagnoses.",
    },
    "NASA-RISKS": {
        "title": "Risks of Human Spaceflight",
        "url": "https://www.nasa.gov/hrp/risks/",
        "use": "Cardiovascular adaptation and sleep risks motivate cautious longitudinal interpretation.",
    },
    "CSA-RADIATION": {
        "title": "Monitoring radiation for astronaut health",
        "url": "https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp",
        "use": "Dedicated radiation instrumentation; our wrist physiology is not dosimetry.",
    },
    "NASA-STRESS-1160": {
        "title": "Individualized Stress Detection System",
        "url": "https://humanresearchroadmap.nasa.gov/Tasks/task.aspx?i=1160",
        "use": "Rationale for considering heart rate, HRV and sleep-wake patterns together.",
    },
    "NASA-ARCHER": {
        "title": "Artemis Research for Crew Health and Readiness",
        "url": "https://www.nasa.gov/reference/archer/",
        "use": "Rationale for activity, sleep and self-report context.",
    },
    "NASA-STANDARD-MEASURES": {
        "title": "Spaceflight Standard Measures",
        "url": "https://www.nasa.gov/reference/standard-measures/",
        "use": "Rationale for repeated standardized observations over time.",
    },
}


def explain(result):
    """Return short display text without deriving a diagnosis or treatment."""
    lines = []
    status = result["status"]
    if status != "available":
        lines.append("No stress estimate is available: " + status.replace("_", " ") + ".")
    else:
        lines.append("This is a research stress indicator, not a diagnosis or proof of its cause.")
    if result["quality"]["status"] == "motion_caution":
        lines.append("Movement may influence these signals. Review activity before interpreting the estimate.")
    pulse_proxy = result.get("feature_pipeline") == "wrist-bvp-eda-acc-60s-v1"
    if pulse_proxy:
        lines.append("RMSSD here is derived from optical pulse intervals, not ECG heartbeats.")
    labels = {"heart_rate_bpm": ("Heart/pulse rate", "beats/min"),
              "hrv_rmssd_ms": ("Pulse-interval RMSSD proxy" if pulse_proxy else "RMSSD indicator", "ms"),
              "eda_microsiemens": ("Skin conductance", "microsiemens")}
    for observation in result["observations"]:
        if "delta" in observation and observation["metric"] in labels:
            label, unit = labels[observation["metric"]]
            lines.append(f'{label} differs from the selected personal reference by {observation["delta"]:+.2f} {unit}.')
    if result["baseline"]["status"] != "available":
        lines.append("A valid personal reference is unavailable; no personal change is inferred.")
    if result["context"]:
        lines.append("Sleep and self-report are displayed as context; they did not alter the model score.")
    lines.append("Review signal quality and the observation trend; this prototype cannot establish medical fitness.")
    lines.append("These wrist measurements cannot determine radiation exposure, bone loss, immune changes or cabin air quality.")
    lines.append("Spaceflight can change physiology; this Earth-trained model has no validated spaceflight correction.")
    return lines
