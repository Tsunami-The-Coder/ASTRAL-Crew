> Historical v1 record. See [FIX_VALIDATION.md](FIX_VALIDATION.md) for the current quality-gated model, five-member support and fresh evaluation.

# NASA challenge resources: wearable evidence review

Reviewed 2026-11-14. Owner: Khalid. AI-assisted source review and implementation.
Scope: wrist measurements, personal references, interpretation and software checks.
This is not a five-hazard diagnostic model, a physiology simulator, or a change to fusion.

## Challenge resources and actual decisions

| Provided resource | Source finding (paraphrased) | Our engineering decision |
|---|---|---|
| [Five Hazards](https://www.nasa.gov/hrp/hazards/) | NASA distinguishes radiation, isolation/confinement, distance, gravity and hostile/closed environments; effects can interact. | Keep hazard coverage explicit in scenarios without treating hazard names as stress labels. |
| [Risks](https://www.nasa.gov/hrp/risks/) | Cardiovascular adaptation, sleep disruption and reduced fitness are separate research concerns. | Personal deltas are descriptive; no automatic gravity correction or diagnosis. Activity can complicate interpretation. |
| [Ongoing HRP Research](https://www.nasa.gov/hrp/ongoing-hrp-research/) | Links to ARCHeR and Standard Measures; the ARCHeR wrist device monitors activity, sleep patterns and light exposure. | Follow the linked studies; do not equate our 60-second motion feature with validated sleep scoring. Light exposure is not an available input here. |
| [CSA radiation monitoring](https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp) | CANS is dedicated neutron-radiation instrumentation. | Expose the wrist sensor's radiation blind spot. Do not manufacture a dose from HRV/EDA. |
| [CSA science in space](https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp) | Space research examines human responses to conditions difficult to reproduce on Earth. | Keep laboratory performance separate from spaceflight validity. |

These pages supply research context, not numerical training rows or validated
coefficients for transforming Earth wrist readings into spaceflight readings.

## Linked studies used for feature decisions

- [Individualized Stress Detection](https://humanresearchroadmap.nasa.gov/Tasks/task.aspx?i=1160): describes combining HR, HRV and sleep-wake patterns. Its resource section lists none. Supports our monitoring rationale, not the validity of optical RMSSD or our classifier.
- [ARCHeR](https://www.nasa.gov/reference/archer/): actigraphy and behavioral surveys around missions, with actigraphy also during flight. Supports recording activity/sleep context; no sleep labels or training files were obtained from this page.
- [Standard Measures](https://www.nasa.gov/reference/standard-measures/): standardized repeated observations, including wrist activity/light and sleep reports, alongside other assessments. Motivates comparable longitudinal observations. Requiring matching extraction methods and window lengths is our implementation decision, not a NASA prescription.

## Measurement audit

| Current quantity | Decision / limit |
|---|---|
| Pulse rate from BVP | Retain as a research feature. Peak detection requires independent reference validation. |
| `hrv_rmssd_ms` | Display as pulse-interval RMSSD proxy. It is not ECG R-R HRV, despite the compatibility field name. |
| EDA | Retain as a WESAD feature. The reviewed NASA pages do not establish its spaceflight stress performance. |
| Motion | Retain caution and context. Mean-centering acceleration is not a physiological microgravity simulation; the 0.2 g scaling is an engineering choice. |
| Sleep/self-report | Retain supplied context without altering the learned score. No sleep detection or chronic-stress diagnosis is implemented. |
| Personal reference | Require one crew member, provenance, extraction pipeline and window duration. Reject incompatible reference deltas while retaining valid current readings. Reference selection still needs human judgment. |

The saved WESAD model has an RMSSD training mean of about 267 ms and a positive
RMSSD coefficient. These values are reasons to audit pulse detection and compare
against synchronized reference measurements; they are not evidence of spaceflight
adaptation or a universal physiological relationship. The existing classification
metric does not establish that individual extracted measurements are accurate.
No numerical model correction or retraining is claimed in this update.

### Reproduced signal-extraction limitation

The `signal_audit.py` probe `sin(2*pi*t) + sin(4*pi*t)` repeats every second,
but v1 reports about 120.09 bpm and 124.88 ms RMSSD. It counts secondary peaks.
The plain 1 Hz sine reports about 59.97 bpm and 2.90 ms RMSSD. These are synthetic
waveform probes, not validated models of astronaut pulse morphology. The result
demonstrates a detector weakness; it does not quantify errors in real WESAD data.
The 85.5% classification result cannot resolve this measurement-validity problem.
Before claiming reliable sensing or retraining for deployment, validate against
synchronized reference beats, improve quality rejection/peak detection, version
the changed features, and repeat participant-held-out evaluation from raw data.
The existing v1 weights remain available for reproducibility and demonstration.

## Five-hazard coverage within the wearable scope

| Hazard | What the wearable scenario checks | What it cannot establish |
|---|---|---|
| Isolation/confinement | Sleep/self-report remain visible context with unchanged model score | Psychiatric diagnosis or chronic stress from one minute |
| Gravity fields | Exercise caution and descriptive personal changes | That gravity caused the change, bone loss, or a corrected flight stress score |
| Radiation | Ordinary-looking wrist readings retain explicit measurement limitations | Absence or amount of radiation exposure |
| Hostile/closed environment | Same wrist readings retain the same output across different hazard narratives | Air quality, infection, or cause of physiological activation |
| Distance from Earth | Inference works without a network; old readings remain stale at receipt time | A delayed reading becoming a current measurement |

`space_scenarios.py` exports nine cases, including reference, sensor failure and
incompatible baselines. All values are arbitrary synthetic engineering fixtures.
Hazard narratives are scenario metadata, not classifier inputs. These cases test
software behavior, not expected astronaut physiology, sensitivity or accuracy.

## Data-access findings and retraining decision

| Candidate | What was verified | Decision |
|---|---|---|
| NASA challenge pages and linked studies above | Descriptions and measurement rationale; no compatible labelled wrist dataset downloaded | Use as design evidence, not training data |
| [NASA Life Sciences Portal](https://www.nasa.gov/hrp/nlsp/) | Agency gateway to human flight and analog research; includes a request process | A possible future source, not an acquired dataset |
| [Standard Measures research paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12612093/) | Describes formal human-data requests, including IRB approval and institutional endorsement | Do not promise immediate access to participant data |
| [NASA Inspiration4 repository article](https://science.nasa.gov/humans-in-space/nasas-repository-supports-research-of-commercial-astronaut-health/) | Confirms biological data in OSDR | Does not by itself establish synchronized BVP/EDA/ACC plus stress labels. An attempted OSD-569 files endpoint could not be read with the research tool; file compatibility remains unverified |
| [OSDR controlled-access guidance](https://www.nasa.gov/reference/osdr-tutorials-requesting-controlled-access-datasets/) | Access restrictions vary by study and file | Inspect files and conditions before selecting data; do not assume all human data are openly downloadable |

No NASA participant data were acquired or used to train this model. This limited
review does not establish that no suitable dataset exists. Before retraining,
verify permission, synchronized sensor channels, sample rates, physical units,
reference labels and independent participants. Different sensors require a new
versioned extraction pipeline. Unlabelled space data may help characterize shifts
but cannot directly validate stress classification. Keep simulation tests separate
from real-data evaluation and do not fit labels invented from our own assumptions.

## Colin handoff

Only wearable-owned files change. `assess` still consumes the same event fields
and returns the same statuses and score semantics. Baselines generated by
`build_baseline` now include `feature_pipeline` and `window_seconds`. Rebuild old
cached baselines; missing metadata is rejected, not guessed. More explanatory
source entries are returned, so consumers should iterate rather than assume a
fixed source count. No fusion, backend, environmental rules or UI changes are included.
