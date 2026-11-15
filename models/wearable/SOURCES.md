# Evidence, provenance and submission notes

Reviewed 2026-11-14. AI-assisted research and implementation; sources below are
primary agency/dataset-owner resources. Summaries are paraphrases, not copied articles.

## NASA sources actually used

| Evidence ID | Source | What it supports | Implementation use / limit |
|---|---|---|---|
| NASA-STRESS-1160 | [Individualized Stress Detection System](https://humanresearchroadmap.nasa.gov/Tasks/task.aspx?i=1160) | Research combining heart rate, HRV and sleep-wake patterns | Physiological monitoring rationale; does not provide our weights or thresholds. Entry lists no downloadable resources. |
| NASA-ARCHER | [Artemis Research for Crew Health & Readiness](https://www.nasa.gov/reference/archer/) | Activity, sleep, wellbeing and interaction monitoring using actigraphy and surveys | Motion context and optional self-report/sleep fields; no inference of sleep from WESAD. |
| NASA-STANDARD-MEASURES | [Spaceflight Standard Measures](https://www.nasa.gov/reference/standard-measures/) | Repeated standardized physiological/psychological observations before/during/after flight | Explicit units, observation windows and prior-person baseline display; our five-window minimum is an engineering choice. |
| NASA-SLEEP-100 | [Sleep loss, circadian desynchronization and workload risk](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=100) | Sleep and performance risk context | Explain why sleep context is displayed separately; no unsupported numerical fatigue model. |
| NASA-HAZARDS | [Five Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/) | Radiation, isolation/confinement, distance, gravity, hostile/closed environments | Missions context and explanation of why offline operation is useful; not five diagnoses derived from a wrist sensor. |
| NASA-RISKS | [Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/) | Distinct physiological and behavioral risks | Scope limits and contextual review; stress scores do not diagnose these conditions. |
| NASA-HRP-RESEARCH | [Ongoing HRP Research](https://www.nasa.gov/hrp/ongoing-hrp-research/) | Index linking relevant studies | Discovery path for ARCHeR and Standard Measures; no direct numerical data ingestion. |

`evidence_ids` in the current per-person output identify the first three design
references plus NASA-HAZARDS, NASA-RISKS and CSA-RADIATION (the CSA radiation link
below). See [NASA_WEARABLE_REVIEW.md](NASA_WEARABLE_REVIEW.md) for the follow-up
challenge-resource audit, source-to-feature decisions and data-access findings.
No complete NASA page is bundled or needed at runtime. References remain visible
in the offline report and documentation; following a link requires internet.

## WESAD: training data, not NASA data

- Dataset: WESAD, Schmidt et al., ICMI 2018.
- DOI: [10.24432/C57K5T](https://doi.org/10.24432/C57K5T).
- [UCI metadata](https://archive.ics.uci.edu/dataset/465/wesad).
- [Original author/university page](https://ubi29.informatik.uni-siegen.de/usi/data_wesad.html).
- [Original archive linked by the authors](https://uni-siegen.sciebo.de/s/HGdUkoNlW1Ub0Gx).
- Published use conditions: scientific, non-commercial use with credit to owners.
  Do not label it unrestricted/public-domain or redistribute the recordings.
- Version: original WESAD.zip; actual archive SHA256 and extraction audit in the
  locally generated evaluation report. No upstream semantic release number assumed.
- Signals used: synchronized wrist BVP 64Hz, EDA 4Hz, ACC 32Hz.
- Units: BVP arbitrary optical amplitude; EDA microsiemens; original wrist ACC
  1/64 g; pulse intervals milliseconds after extraction.
- Labels: 1 baseline, 2 stress, 3 amusement; binary training uses 2 vs 1/3.
  Excluded: 0, 4, 5, 6, 7 and mixed windows. Validate against archive README.
- Transformation: 60-second non-overlapping windows and signals.py extraction;
  training-only standardization in each participant-held-out fold.
- Limits: laboratory protocol, 15 individuals, pulse artifacts, no astronaut
  labels, no synchronized voice recordings, no sleep labels for this model.
- Distribution: no raw recordings are committed. `model.json` contains fitted
  coefficients and preprocessing parameters for this scientific, non-commercial
  prototype. Preserve WESAD attribution and use conditions. Team members can
  reproduce training using the source and commands in README.md.

Credit: Philip Schmidt, Attila Reiss, Robert Duerichen, Claus Marberger,
Kristof Van Laerhoven, *Introducing WESAD, a multimodal dataset for Wearable
Stress and Affect Detection*, ICMI 2018. Published baseline results are not our results.

## Other resources considered; not claimed as ingested data

- [NASA Life Sciences Portal](https://nlsp.nasa.gov/): candidate future human
  research source; some records require data requests. No NASA human training
  dataset was ingested in this component.
- [NASA OSDR](https://osdr.nasa.gov/): no specific compatible accession selected;
  do not list OSDR as a used training dataset.
- [CSA radiation monitoring](https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp):
  background for a separate dosimeter/environment workstream. Not evidence that
  HRV/EDA can measure radiation exposure.
- [CSA science in space](https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp):
  background on space research, not a classifier dataset or validation source.

## Synthetic material

All inputs in demo.py, voice mocks, CO2 scenarios, baseline examples and fixture
coefficients are AI-assisted synthetic constructions. They represent no person.
The research model's use on synthetic demo inputs does not convert them into
astronaut observations. Independent voice and wearable recordings must not be
described as synchronized real measurements.

## Submission wording and limits

Suggested factual description (update after team integration):

> Our wearable prototype uses NASA HRP research on individualized stress
> monitoring, ARCHeR, and Standard Measures to guide physiological indicators,
> activity/sleep context, and longitudinal presentation. Its research classifier
> is developed separately using the non-NASA WESAD ground-laboratory dataset.
> Five-person mission demonstrations use explicitly synthetic telemetry. NASA
> sources inform the design; they do not establish clinical or astronaut validity.

The supplied 2026 Project Submission Guide (published November 13) requires at
least one NASA data/resource for Global Award eligibility, source attribution,
English submission materials, an openly accessible final project/demo, and a
demo limited to <=7 slides or <=30 seconds. The current repository is private;
the team must choose an appropriate publicly accessible submission artifact.
This change does not alter repository visibility or submit the project.

AI disclosure: code, documentation and synthetic fixtures were produced with
Codex assistance and reviewed with actual tests. Disclose this in descriptive
text and metadata. No NASA logos or mission branding are generated here.

Current evaluation and privacy audit: see FIX_VALIDATION.md. Public examples use synthetic crew IDs; no personal health recordings are bundled.
