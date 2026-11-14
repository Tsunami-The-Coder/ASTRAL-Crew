# ASTRAL Crew — project submission draft

## Project name

**ASTRAL Crew — Adaptive Spaceflight Telemetry, Resilience & Astronaut Life-support Intelligence**

**Tagline:** Know what is changing. Know what to check next.

## Summary

**Eleni’s role:** NASA research, dataset access checks, provenance, and scientific citations. The interface and software prototype are collaborative team work; individual responsibilities are listed in the repository.


ASTRAL Crew is an offline-first astronaut health-monitoring prototype for long-duration missions. It combines a daily self-check with an individual's recent health history, NASA's human-spaceflight hazard framework, and a separately labeled chart of real NASA Inspiration4 serum chemistry data. Instead of treating an isolated number as a diagnosis, it helps an astronaut notice a pattern change, verify a measurement, consider context, and follow an approved mission procedure.

## Challenge and solution

On a mission far from Earth, communication delays and limited onboard resources make clear self-assessment valuable. A list of measurements alone may not show whether a value is changing for a particular astronaut or whether several indicators have shifted together.

ASTRAL joins the team's Digital Health Twin concept with a practical self-check and evidence view:

1. **SENSE** records heart rate, heart-rate variability, sleep, exercise, oxygen saturation, body temperature, blood pressure, mood, and an optional symptom note. The daily demo values are synthetic or manually entered.
2. **INTELLIGENCE** compares selected readings with recent personal history using a transparent rolling median and median absolute deviation (MAD) rule. The output names readings that differ from the recent pattern; it does not infer why.
3. **BIOLOGY** plots five measured serum chemistry analytes from NASA OSDR OSD-575, selectable by the reviewer: glucose, creatinine, sodium, potassium, and calcium. Each series shows all seven sample timepoints for each of four pseudonymous crew codes.
4. **ENVIRONMENT** organizes mission context around NASA's five human-spaceflight hazards and separates habitat context from individual measurements.
5. **RESPONSE** guides the astronaut to repeat an unexpected measurement, check recent context, and follow the approved mission procedure if concern remains.

## What is implemented

- Responsive browser dashboard with overview, daily check-in, crew context, hazards, NASA Biology evidence, and sources/method views.
- Synthetic personal history and a clearly labeled simulated change scenario.
- An interactive NASA dataset chart showing five analytes from 28 serum samples, grouped by crew code and collection timepoint.
- Browser-local storage with a clear-data control; the static NASA data chart also works offline.
- An English source map, data provenance note, seven-slide demo, and short demo narration.

## NASA data integration and interpretation

NASA OSDR OSD-575 is the SpaceX Inspiration4 serum metabolic panel and immune/cardiac cytokine study. The bundled transformed comprehensive metabolic panel file contains 28 samples for four crew codes, seven timepoints each: L−92, L−44, L−3, R+1, R+45, R+82, and R+194. Those are pre-flight and post-flight collections around a three-day low Earth orbit mission; this CMP series does not provide daily wearable values or in-flight measurements.

ASTRAL displays source values for five analytes, without aggregation or fitting a model. The chart's shaded band reflects the laboratory reference interval in the data file. It is contextual information, not a clinical threshold for astronauts. The small cohort and sparse sampling cannot validate ASTRAL's daily personal trend rule. NASA OSDR study metadata and the exact file hash, license, and transformation are documented in [data/README.md](data/README.md).

NASA's 5 Hazards of Human Spaceflight structure the Mission Hazards view. CSA's radiation-monitoring article and space-experiment overview inform background text only; no CSA dataset or sensor feed is connected. See [REFERENCES.md](REFERENCES.md) for the complete source-use map.

## Scientific and technical validity

The challenge's example indicators inform the daily form. The personal trend comparison is a transparent demonstration, not a clinically validated threshold or predictive model. It requires at least five comparison readings. All generated daily check-in and cabin values are labeled synthetic. ASTRAL does not diagnose, predict disease, infer causes, recommend medication, or control spacecraft systems.

## 30-second demo story

Begin with the synthetic personal check-in and recent trend. Load the simulated scenario to show a pattern change, then show ASTRAL's verification and procedure guidance. Open Biology Evidence and select serum glucose to view the 28 actual NASA OSDR sample values across seven timepoints for four coded crew members. State that this is real human spaceflight data but sparse post/pre-flight serum sampling, not continuous wearable monitoring or validation of ASTRAL's personal comparison rule.

## Seven-slide demo outline

1. **ASTRAL Crew** — challenge, purpose, and team presenter.
2. **A single reading needs context** — five NASA human-spaceflight hazards and the self-assessment problem.
3. **A small workflow** — check in, compare, verify, and act under the approved mission procedure.
4. **Prototype walkthrough** — explicitly synthetic heart-rate, sleep, and HRV example with a verification-oriented response.
5. **NASA evidence** — actual OSDR OSD-575 serum glucose values for four coded crew across seven pre/post-flight timepoints.
6. **Scientific boundaries** — measured versus synthetic data and what ASTRAL does not claim.
7. **Impact and next steps** — a focused self-assessment contribution, expert review/validation needs, team roles, and sources.

## AI/SI-use disclosure draft

The team supplied the original ASTRAL concept and initial five-component architecture. Generative AI assisted with feasibility review, interface and submission wording, HTML/CSS/JavaScript implementation, and preparation of the demo deck. Team members reviewed and take responsibility for the final project, claims, citations, dataset handling, and code. AI use must be disclosed in the official project form in accordance with the participant guide. No AI-generated images, audio, video, NASA marks, or NASA logos are used.

## Final submission checklist

- Complete and proofread the official Project Submission page in English.
- Confirm every member is registered for the same event and listed on the team page.
- Make the code repository reachable to judges, and add both repository and public demo URLs to the official submission.
- Ensure the demo and linked materials open without sign-in.
- Disclose AI assistance accurately and list external code, text, data, and image sources.
- Confirm team-member names and identifying media comply with the official guide and Terms, especially for under-18 participants.
- Obtain required team agreements and submit through the Team Project page before the Team Owner's applicable local-time deadline.
