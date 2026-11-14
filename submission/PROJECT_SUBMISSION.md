# ASTRAL Crew — project submission draft

## Project name

**ASTRAL Crew — Adaptive Spaceflight Telemetry, Resilience & Astronaut Life-support Intelligence**

**Tagline:** Know what is changing. Know what to check next.

## Summary

ASTRAL Crew is an offline-first astronaut health-monitoring prototype for long-duration missions. It combines a daily self-check with an individual's recent health history and NASA's human-spaceflight hazard framework. Instead of presenting an isolated number as a diagnosis, it helps the astronaut notice a change, verify the measurement, review context, and follow an approved mission procedure. A NASA OSDR evidence view explains how spaceflight biology research can inform the context while distinguishing that research from the prototype's synthetic demo values.

## Challenge and solution

On a mission far from Earth, communication delays and limited onboard resources make timely, clear self-assessment important. A list of measurements alone may not show whether a value is changing for a particular astronaut or whether several indicators have shifted together.

ASTRAL brings the team's Digital Health Twin idea together with a usable individual check-in. Its five components are:

1. **SENSE:** record heart rate, heart-rate variability, sleep, exercise, oxygen saturation, body temperature, blood pressure, mood, and an optional symptom note.
2. **INTELLIGENCE:** compare selected readings with the astronaut's own recent history using a transparent rolling median and median absolute deviation (MAD) rule. The output names readings that differ from the recent pattern; it does not infer why.
3. **BIOLOGY:** show study metadata and the sample timeline for NASA OSDR OSD-575, an Inspiration4 serum study. The interface explains why these sparse samples are biological research context rather than wearable data or validation of ASTRAL.
4. **ENVIRONMENT:** frame mission health context using NASA's five hazards of human spaceflight. Any demo habitat readings are labeled simulated; no spacecraft sensor is connected.
5. **RESPONSE:** guide the astronaut to re-check an unexpected measurement, consider recent sleep, workload, and exercise context, and follow the crew's approved medical procedure if concern remains.

## What is implemented

- Responsive browser dashboard with six views: overview, daily check-in, crew context, mission hazards, biology evidence, and sources/method.
- Synthetic historical values and a simulated multi-indicator change scenario.
- Local trend chart and an explainable personal-pattern flag.
- Browser-only local storage and a clear-data control.
- Source attribution and limitations embedded in the interface and this repository.

## Scientific and technical validity

The indicator list follows the 2026 challenge prompt. The anomaly comparison is a transparent demonstration of personal trend monitoring, not a medical threshold or validated model. It requires at least five comparison readings and uses a rolling personal median with a MAD-based deviation rule. All synthetic scenario readings are labeled. No clinical interpretation or causal conclusion is generated. The workflow is offline and has no safety-critical connection.

## NASA and partner-resource integration

- NASA's **5 Hazards of Human Spaceflight** structure the Mission Hazards view and the links between mission context and health indicators.
- NASA OSDR **OSD-575** provides the named study, assay description, sample count, and collection timeline shown in Biology Evidence. No raw astronaut readings are displayed or analyzed.
- The NASA OSDR FAQ informs the source/method explanation of repository data; it is not an additional dataset.
- The CSA radiation-monitoring article informs the radiation-monitoring context and rationale. It is not a live feed and no CANS sensor data or CSA dataset is integrated.
- The CSA page on conducting science in space informs the explanation of why space-based human research matters. It contributes no measurements to the prototype.

See [REFERENCES.md](REFERENCES.md) for URLs, use locations, and data-use boundaries.

## Demo scenario

Start with the nominal synthetic check-in. Load the sample scenario, where resting heart rate shifts upward, sleep decreases, HRV changes, and exercise is below the recent pattern. Save it. ASTRAL names the changed indicators, states it cannot determine their cause, and recommends repeating unexpected measurements, reviewing context, and following the approved mission procedure if concern persists. Then open Biology Evidence to show what the OSDR study does—and does not—support.

## Seven-slide demo outline

1. **ASTRAL Crew** — project name, team, challenge, one-sentence purpose.
2. **The mission problem** — long communication delays make clear self-assessment valuable.
3. **SENSE** — enter or review today's measurements and self-report.
4. **INTELLIGENCE + RESPONSE** — show the synthetic scenario, personal trend comparison, and safe review sequence.
5. **BIOLOGY** — show OSD-575 metadata and explain its sample type, schedule, and limits.
6. **ENVIRONMENT** — connect the dashboard to NASA's five hazards; distinguish context from measured data.
7. **Impact, limits, and sources** — offline workflow, privacy boundary, non-diagnostic nature, no autonomous controls, references.

## AI/SI-use disclosure draft

The team supplied the original ASTRAL concept and initial five-component architecture. Generative AI was used to review feasibility, edit interface and submission wording, and assist with HTML, CSS, and JavaScript implementation. Team members reviewed and take responsibility for the final project, claims, citations, and code. AI use must be disclosed in the official project form in accordance with the current participant guide. No AI-generated images, audio, video, or NASA marks are used.

## References

See [REFERENCES.md](REFERENCES.md) for the complete source list and precise account of how each source is used.

## Final submission checklist

- Complete and proofread the official Project Submission page in English.
- Confirm every member is registered for the same event and listed on the team page; check the event-specific eligibility rules.
- Add the final public demo and repository links to the official submission.
- Ensure the demo and linked materials are reachable without sign-in.
- Disclose AI assistance accurately; list external code, text, data, and image resources as applicable.
- Confirm team-member names and identifying media comply with the official guide and Terms, especially for under-18 participants.
- Obtain the required team agreements and submit through the Team Project page before the deadline stated for the Team Owner's event.
