"""Synthetic dosimeter accounting, not radiation transport or risk prediction."""

from dataclasses import asdict, dataclass
from math import isfinite


@dataclass(frozen=True)
class RadiationConfig:
    baseline_rate_msv_per_day: float = 1.8
    elevated_multiplier: float = 4.0

    def __post_init__(self):
        for name, value in asdict(self).items():
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError(f'{name} must be finite and nonnegative')
        if self.elevated_multiplier < 1:
            raise ValueError('elevated_multiplier must be at least 1')


def radiation_reading(elapsed_seconds, *, elevation_start_seconds=None,
                      config=RadiationConfig()):
    """Integrate a constant rate with an optional step increase.

    Day means 86400 Earth seconds. Dose starts at zero for EACH scenario run.
    Everyone shares the same exposure assumption; individual shielding, activity,
    organ dose, radiation spectrum, and lifetime history are not modeled.
    """
    for value in (elapsed_seconds, elevation_start_seconds):
        if value is not None and (type(value) not in (int, float) or not isfinite(value) or value < 0):
            raise ValueError('times must be finite nonnegative seconds')
    if elapsed_seconds is None:
        raise ValueError('elapsed_seconds is required')
    elevated_seconds = (max(0, elapsed_seconds - elevation_start_seconds)
                        if elevation_start_seconds is not None else 0)
    baseline_seconds = elapsed_seconds - elevated_seconds
    elevated = elevation_start_seconds is not None and elapsed_seconds >= elevation_start_seconds
    rate = config.baseline_rate_msv_per_day * (config.elevated_multiplier if elevated else 1)
    dose = config.baseline_rate_msv_per_day * (
        baseline_seconds + config.elevated_multiplier * elevated_seconds) / 86400
    return {
        'data_origin': 'synthetic',
        'dose_equivalent_rate_msv_per_day': rate,
        'dose_equivalent_since_run_start_msv': round(dose, 9),
        'quality': 'available',
        'career_dose_msv': None,
        'limitations': 'Illustrative exposure accounting; no personal risk, career-limit, or solar-event diagnosis.',
    }
