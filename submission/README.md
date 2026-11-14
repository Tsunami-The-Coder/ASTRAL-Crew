# ASTRAL Crew — submission package

**Adaptive Spaceflight Telemetry, Resilience & Astronaut Life-support Intelligence**  
NASA Space Apps Challenge 2026 · Create Health Monitoring Software for Astronauts on Space Missions

> **State:** interactive educational prototype. Daily check-in and habitat examples are synthetic. The separate Biology view contains public NASA OSDR sample-level data. This is not a medical device or flight-certified software.

## Open the prototype

Open [`astral-prototype/index.html`](astral-prototype/index.html) in a modern browser. No build step, account, network access, API key, or external JavaScript library is required. The published demo is [ASTRAL Crew](https://astral-crew-health.eleftherialili81.chatgpt.site/).

## Eleni’s contribution

Eleni’s team role is NASA research, data-source verification, provenance, and scientific citations. The project’s interface and code are collaborative work; the repository team plan records each workstream.

## The idea

Long-duration crews need a clear way to notice health changes, review them against personal patterns, and choose an appropriate next step when communication with Earth is delayed. ASTRAL combines the team's Digital Health Twin concept with an individual daily check-in, NASA's human-spaceflight hazard framework, and a separate view of real NASA human spaceflight biology data.

### Five connected components

- **SENSE:** enter heart rate, HRV, sleep, exercise, SpO₂, body temperature, blood pressure, mood, and an optional symptom note.
- **INTELLIGENCE:** compare selected readings with recent personal history using a transparent rolling median and median absolute deviation (MAD) rule. A changed pattern prompts review; it does not explain the cause.
- **BIOLOGY:** interact with five analytes from the actual NASA OSDR OSD-575 transformed serum chemistry file, plotted for four pseudonymous crew codes across seven collection times.
- **ENVIRONMENT:** organize mission context around NASA's five human-spaceflight hazards. Cabin readings in the demo are labeled synthetic.
- **RESPONSE:** guide the user to repeat unexpected measurements, check personal context, and follow an approved mission procedure when concern remains.

## What is implemented

- Responsive interactive dashboard with overview, check-in, crew context, hazards, NASA Biology evidence, and sources/method views.
- Seven synthetic check-ins and a simulated multi-indicator example for the daily-monitoring workflow.
- A local trend chart with an illustrative per-person pattern comparison.
- A NASA OSDR chart with measured serum glucose, creatinine, sodium, potassium, and calcium values, separated by anonymized crew code and sample timepoint.
- A source-supplied lab reference interval shown as context in the chart; no diagnosis or astronaut-specific operational threshold is inferred.
- Browser-local storage for user-entered demo check-ins and a clear-data control.
- The team repository also contains a separate WESAD-trained experimental wearable model. It is not connected to this browser prototype; its laboratory-only limits and known pulse-detection issue are documented in the model card.

## NASA data and scientific limits

The chart uses the public transformed CMP file from NASA OSDR OSD-575. It has 28 serum samples from four Inspiration4 crew codes, seven collections per person: L−92, L−44, L−3, R+1, R+45, R+82, and R+194. The dataset covers pre-flight and post-flight collections around a three-day mission. It does not provide continuous daily wearable readings or in-flight measurements in this CMP file.

ASTRAL plots the selected sample values without aggregating them, training a model, or using them as a personal baseline. The reference intervals printed in the source file are visible context only. Four participants and sparse samples cannot establish population-level relationships or validate a daily monitoring rule. Calcium is not a bone-density measurement.

The NASA OSDR source CSV is included under [`data/`](data/). The chart also embeds the five selected source fields so it works offline. All daily check-in and habitat demo values remain synthetic. No live wearable, spacecraft sensor, NASA telemetry feed, audio recording, server, or external API is connected.

## Privacy and use

User-entered demo values stay in the current browser's local storage. The bundled NASA OSDR chart data is public research data under the source study's CC0-1.0 license. Do not enter real personal or medical information into a public demonstration.

## Run locally

1. Download or clone the repository.
2. Open `submission/astral-prototype/index.html` in a modern browser.
3. Use **Daily check-in** for the synthetic scenario or **Biology evidence** to explore the NASA source values.

## Project materials

- [Project submission narrative and seven-slide outline](PROJECT_SUBMISSION.md)
- [Source-by-source provenance and use map](REFERENCES.md)
- [30-second demo narration](DEMO_SCRIPT.md)
- [NASA OSDR data provenance](data/README.md)
- [Eleni’s team submission checklist](ELENI_CHECKLIST.md)
- [Editable seven-slide demo deck](ASTRAL_Crew_Demo.pptx)

## AI assistance disclosure

The team supplied the original ASTRAL concept and initial five-component architecture. Generative AI assisted with feasibility review, interface and submission copy editing, and HTML/CSS/JavaScript implementation. The team should review the final work, understand the code, verify sources and claims, and disclose assistance accurately in the official submission. No AI-generated images, audio, video, NASA marks, or NASA logos are included.

ASTRAL Crew is an independent participant project. NASA and the Canadian Space Agency do not endorse this prototype and are not responsible for its content.
