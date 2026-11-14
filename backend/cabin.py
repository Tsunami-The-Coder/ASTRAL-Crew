"""Simplified, well-mixed CO2 balance for synthetic fixtures only."""

from dataclasses import dataclass, asdict
from math import isfinite


@dataclass(frozen=True)
class CabinConfig:
    volume_m3: float = 100.0
    temperature_k: float = 295.15
    pressure_kpa: float = 101.0
    initial_co2_percent: float = 0.10
    co2_kg_per_person_day: float = 1.04
    removal_fraction: float = 0.0

    def __post_init__(self):
        for key, value in asdict(self).items():
            if type(value) not in (int, float) or not isfinite(value):
                raise ValueError(f"{key} must be a finite number")
        for key in ("volume_m3", "temperature_k", "pressure_kpa"):
            if getattr(self, key) <= 0:
                raise ValueError(f"{key} must be positive")
        if not 0 <= self.initial_co2_percent < 100:
            raise ValueError("initial_co2_percent must be in [0, 100)")
        if self.co2_kg_per_person_day < 0 or not 0 <= self.removal_fraction <= 1:
            raise ValueError("production must be nonnegative; removal_fraction must be 0..1")


def co2_percent_after(elapsed_seconds, crew_count, config=CabinConfig()):
    """Ideal-gas trace balance with constant pressure/temperature and production.

    Removal fraction is the fraction of ongoing crew production removed, not
    hardware efficiency. 1 balances production; 0 removes none. Fixed pressure
    assumes unmodeled pressure regulation. No leak, O2 balance, local pockets,
    scrubber dynamics, or human symptom response is predicted.
    """
    if type(elapsed_seconds) not in (int, float) or not isfinite(elapsed_seconds) or elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be finite and nonnegative")
    if type(crew_count) is not int or crew_count < 1:
        raise ValueError("crew_count must be a positive integer")
    cabin_moles = config.pressure_kpa * 1000 * config.volume_m3 / (8.314462618 * config.temperature_k)
    produced_kg = crew_count * config.co2_kg_per_person_day * elapsed_seconds / 86400
    retained_moles = produced_kg * (1 - config.removal_fraction) * 1000 / 44.01
    concentration = config.initial_co2_percent + 100 * retained_moles / cabin_moles
    if concentration >= 100:
        raise ValueError("configuration exceeds the model's concentration domain")
    return concentration
