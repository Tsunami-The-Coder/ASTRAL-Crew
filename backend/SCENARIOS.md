# Synthetic scenario assumptions

These fixtures are engineering test inputs, not recorded mission data, trained
inference, physiological predictions, or an approved shared interface. Version:
`internal-v4` for generated sequences. Sources checked November 14, 2026; no external data is downloaded
or redistributed. Runtime uses only Python's standard library and local SQLite.

The internal demo defaults to five crew; `--crew-count 4` retains original mission
compatibility. AST-05 uses illustrative centers of 70 bpm, 46 ms RMSSD, and 1.3
microsiemens EDA. These remain unvalidated demo assumptions. The shared team
roster is unchanged pending coordination. Persistent reference profiles are
separate from scenario readings and are not updated by incidents.

## Source context versus chosen parameters

- [MedlinePlus: Vital signs](https://medlineplus.gov/ency/article/002341.htm)
  describes 60–100 bpm as a typical healthy adult resting pulse range. Our chosen
  crew centers (65–75 bpm) and bounded +/-2 bpm variation sit inside this range.
  This does not establish astronaut-specific normality or individual baselines.
- [NASA OCHMO-TB-004 Rev D, March 10, 2026](https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-004-carbon-dioxide.pdf)
  discusses CO2 monitoring, pressure, exposure duration, and uncertainty in
  cognitive effects. Our 0.10% starting point is an illustrative choice, not a
  NASA-approved scenario or instantaneous alarm limit. The former arbitrary
  0.50% endpoint has been replaced by the balance calculation below.
  Partial pressure requires total pressure: ppCO2 = CO2_percent / 100 * pressure.
  At 101 kPa, 0.50% gives approximately 0.505 kPa (3.79 mmHg).

HRV centers 41–52 ms, EDA centers 1.1–1.7 microsiemens, their jitter, and the
scripted changes are unvalidated demo assumptions needing Eleni's review. They
are not diagnostic ranges. O2 near 21% and pressure near 101 kPa describe the
chosen Earth-like demo cabin, not a specification for all spacecraft atmospheres.
Uniform bounded noise is for repeatable testing, not a realistic sensor-noise
distribution. A simplified CO2 balance now exists; no causal physiological model exists.

## Scenarios

- `baseline`: small independent jitter around fixed crew and cabin centers. 
- `co2_rise`: after the first quarter, removal drops to the configured fraction
  of crew production; the calculated CO2 concentration increases. Scripted crew
  HR rises up to 18 bpm, HRV falls up to 10 ms, and EDA rises up to 0.8
  microsiemens. These co-occurring changes exercise future correlation rules;
  they do not model CO2-induced stress, symptoms, panic, or cognitive impairment.
- `missing_sensor`: halfway through, cabin CO2 and AST-01 EDA become null and
  are marked missing. No normal replacement values are supplied.
- `faulty_sensor`: halfway through, AST-01 HR becomes -10 bpm and is marked
  invalid. This is deliberately impossible input, not a true crew condition.

Quality fields are simulator ground truth, not automated detection results.
Voice, wearable inference, and assessments remain null in every scenario.
One sample represents one minute; default duration is 12 samples. There is no
wall-clock waiting. Reusing a seed repeats values; timestamps are assigned on save.
Scenario metadata and quality fields are internal fixture details pending review.

## Simplified cabin balance

NASA's [Life Support Baseline Values and Assumptions, Rev 1 (2018)](https://ntrs.nasa.gov/api/citations/20180001338/downloads/20180001338.pdf)
lists 1.04 kg CO2 per crew member per day, based on a daily activity profile
including exercise. We approximate that daily load as constant; it is not an
instantaneous resting production measurement. The 100 m3 volume, 295.15 K
temperature, initial CO2, and removal schedule are configurable demo assumptions.

The ideal-gas approximation uses:

```
cabin_moles = pressure_Pa * volume_m3 / (8.314462618 * temperature_K)
retained_CO2_moles = crew * kg_per_person_day * seconds / 86400
                     * (1 - removal_fraction) * 1000 / 44.01
CO2_percent = initial_percent + 100 * retained_CO2_moles / cabin_moles
```

Removal fraction 1 balances production; 0 removes none. It is not a physical
scrubber efficiency specification. The model assumes well-mixed gas at regulated
constant pressure and temperature, neglecting detailed gas exchanges and removal
dynamics. O2 remains illustrative and independently regulated, not an O2 balance.
This is a short-duration trace-gas approximation, not a validated spacecraft
simulator. Its parameters are included in stored fixture metadata, which must
not be used as diagnostic evidence by cross-analysis.

[NASA's CO2 brief](https://www.nasa.gov/ochmo-tb-004-carbon-dioxide-2/)
explains exhaled CO2 and removal equipment. Insufficient removal can cause buildup;
poor ventilation can cause local accumulation, which this well-mixed model cannot
resolve. A CO2 rise does not establish a cabin leak or crew symptoms.


## Radiation module: synthetic dose-equivalent accounting

Each crew now has a radiation object with rate in mSv/day, dose in mSv **since
this scenario run started**, data origin, quality, limitations, and null career
dose. All crew share the same modeled exposure; no individual shielding or
organ-specific dosimetry is inferred. New runs reset the scenario dose; do not
sum cumulative snapshots or combine resets into a career history.

The configurable 1.8 mSv/day default is illustrative transit context, based on
[SwRI's RAD mission investigators' summary (2013)](https://www.swri.org/newsroom/press-releases/swri-scientists-publish-first-radiation-measurements-the-surface-of-mars).
It is a historical spacecraft measurement context, not a fixed Mars mission
exposure, absorbed dose in mGy, or personal effective-dose measurement.
[NASA's RAD comparison](https://science.nasa.gov/resource/radiation-exposure-comparisons-with-mars-trip-calculation/)
provides additional expedition-dose context. These are references, not downloaded
sensor datasets. Review applicability with Eleni before final scientific claims.

The `radiation_rise` scenario increases rate halfway through by a configurable
factor (default 4, an unsupported engineering test choice). Rate changes are
integrated piecewise: dose = sum(rate_mSv_per_day * duration_seconds / 86400).
There is no physiological response model, identified solar storm, clinical
threshold, career limit comparison, or automated shelter action. Biometric
changes are not scripted in response to this radiation event.

The missing_sensor case sets AST-01 radiation rate and accumulated dose to null
with missing quality after halfway. Other crew remain available. The displayed
cumulative dose is unavailable rather than a fabricated continuation.

Cross-analysis now flags configured rate increases for recommended review;
these demo comparisons are not a validated radiation safety alert engine. The generic storage and service retain the fields
without dropping or interpreting them. Units and new radiation fields remain
internal fixture choices pending shared-contract review.
