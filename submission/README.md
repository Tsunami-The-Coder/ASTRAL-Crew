# ASTRAL Crew — submission package

**Adaptive Spaceflight Telemetry, Resilience & Astronaut Life-support Intelligence**  
NASA Space Apps Challenge 2026 · Create Health Monitoring Software for Astronauts on Space Missions

> **Project state:** interactive educational prototype. All example health and habitat readings are synthetic. This is not a medical device, clinical decision system, or flight-certified software.

## Open the prototype

Open [`astral-prototype/index.html`](astral-prototype/index.html) in a modern browser. No build step, account, internet connection, API key, or third-party JavaScript library is required. The published demo is available at [ASTRAL Crew](https://astral-crew-health.eleftherialili81.chatgpt.site).

## The idea

Long-duration crews need a clear way to notice health changes, review them against their own recent patterns, and choose an appropriate next step when communication with Earth is delayed. ASTRAL joins the team's Digital Health Twin concept with a practical daily self-check and mission-hazard context. It turns several indicators into a small, explainable review workflow rather than an opaque diagnosis.

### Five connected components

- **SENSE** — enter heart rate, HRV, sleep, exercise, SpO₂, body temperature, blood pressure, mood, and an optional symptom note.
- **INTELLIGENCE** — compare selected readings with the user's recent history using a transparent rolling median and median absolute deviation (MAD) rule. A changed pattern prompts review; it does not explain the cause.
- **BIOLOGY** — show a NASA OSDR Inspiration4 study timeline and assay context, with the limits of those data explained.
- **ENVIRONMENT** — organize mission context around NASA's five human-spaceflight hazards. Any cabin values in the demo are labeled simulated.
- **RESPONSE** — guide the user to repeat unexpected measurements, check recent context, and use the crew's approved medical procedure if concern remains.

## What the prototype demonstrates

- Responsive interactive dashboard with overview, check-in, crew context, hazards, biology evidence, and methods/resources views.
- Seven synthetic historical check-ins and a clearly labeled synthetic multi-indicator scenario.
- A local trend chart and per-person pattern comparison. The rule requires at least five comparison readings and is illustrative, not clinically validated.
- Browser-local storage with a control to clear local demo entries.
- Source links and an explicit record of which evidence informs which interface element.

## Data and inference limits

- No wearable, spacecraft sensor, NASA telemetry, audio recording, voice classifier, server, or live API is connected.
- No WESAD, SUSAS, or Artemis audio files are bundled, trained on, or analyzed by this prototype.
- NASA OSDR OSD-575 is represented by study metadata and a published collection timeline. Raw participant records are not displayed or analyzed here; the study is not a continuous wearable dataset and is not used to train or validate the demo trend rule.
- Trend flags are not clinical thresholds. ASTRAL does not diagnose, predict disease, infer psychological or environmental causes, recommend medication, or control spacecraft systems.
- Data entered into the demo stays in the current browser's local storage. Do not enter real medical or identifying information into a public demonstration.

## Run locally

1. Download or clone the repository.
2. Open `submission/astral-prototype/index.html` in a modern browser.
3. Use **Daily check-in** or load the clearly labeled simulated scenario. Use **Sources & method** to review provenance and limits.

## Project materials

- [Project submission narrative, references, AI-use statement, and seven-slide demo outline](PROJECT_SUBMISSION.md)
- [Source-by-source provenance and use map](REFERENCES.md)
- [Short demo narration](DEMO_SCRIPT.md)

## AI assistance disclosure

The team provided the original ASTRAL concept and initial five-component architecture. Generative AI assisted with feasibility review, interface and submission copy editing, and HTML/CSS/JavaScript implementation. The team should review and understand the final prototype, verify claims and links, and disclose this assistance accurately in the official submission. No AI-generated imagery, audio, video, NASA marks, or NASA logos are included.

## Independence

ASTRAL Crew is an independent participant project. NASA and the Canadian Space Agency do not endorse this prototype and are not responsible for its content. Their publicly accessible resources are cited for the specific educational roles documented in [REFERENCES.md](REFERENCES.md).
