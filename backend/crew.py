"""Internal synthetic crew configuration, independent of UI/model contracts."""

DEMO_BASELINES = (
    (68, 48, 1.2), (72, 44, 1.5), (65, 52, 1.1), (75, 41, 1.7),
    (70, 46, 1.3),
)


def demo_profiles(crew_count=5):
    """Fresh synthetic profiles; reference values are not clinical baselines.

    Four remains supported for the original mission plan. Change this internal
    configuration only; the team still needs to approve the integration roster.
    """
    if type(crew_count) is not int or not 1 <= crew_count <= len(DEMO_BASELINES):
        raise ValueError("crew_count must be an integer between 1 and 5")
    return [
        {
            "crew_id": f"AST-{index:02}",
            "data_origin": "synthetic",
            "profile_version": "demo-v1",
            "limitations": "Illustrative reference values, not measured personal baselines.",
            "baseline": {
                "heart_rate_bpm": heart_rate,
                "hrv_rmssd_ms": hrv,
                "eda_microsiemens": eda,
            },
        }
        for index, (heart_rate, hrv, eda) in enumerate(DEMO_BASELINES[:crew_count], 1)
    ]
