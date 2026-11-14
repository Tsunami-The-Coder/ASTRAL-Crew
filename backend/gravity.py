"""Illustrative microgravity trend; no densitometry or clinical prediction."""

from dataclasses import asdict, dataclass
from math import isfinite


@dataclass(frozen=True)
class GravityConfig:
    illustrative_loss_percent_per_30_days: float = 1.0

    def __post_init__(self):
        value = self.illustrative_loss_percent_per_30_days
        if type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= 1.5:
            raise ValueError('demo loss rate must be finite and between 0 and 1.5 percent per 30 days')


def gravity_record(microgravity_days, config=GravityConfig()):
    """Linear normalized trend over 0..180 exposure days, solely for a demo.

    No extrapolation to Mars partial gravity or effects of exercise/treatment.
    Measured bone density and cardiovascular assessment remain unavailable.
    """
    if (type(microgravity_days) not in (int, float) or not isfinite(microgravity_days)
            or not 0 <= microgravity_days <= 180):
        raise ValueError('microgravity_days must be finite and within the demo domain 0..180')
    loss = config.illustrative_loss_percent_per_30_days * microgravity_days / 30
    return {
        'data_origin': 'simulated_inference',
        'model_version': 'illustrative-gravity-v1',
        'microgravity_exposure_days': microgravity_days,
        'parameters': asdict(config),
        'illustrative_bone_density_percent_of_start': round(100 - loss, 3),
        'measured_bone_density_g_per_cm2': None,
        'cardiovascular_assessment': None,
        'measurement_status': 'unavailable',
        'limitations': [
            'Educational linear trend, not a measurement or validated personal prediction.',
            'Does not model skeletal sites, exercise, treatment, recovery, or partial gravity.',
            'Not inferred from voice, heart rate, HRV, or EDA.',
        ],
    }
