# ASTRAL Crew — sources, use, and provenance

This file distinguishes information used to design the prototype from data actually processed by it. Public links are provided so a judge can verify the sources.

| Source | How it is used in ASTRAL | Data actually analyzed by this prototype? |
| --- | --- | --- |
| NASA Space Apps 2026 challenge brief — [Create Health Monitoring Software for Astronauts on Space Missions](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/) | Defines the challenge, self-assessment purpose, example health indicators, and design context. | No. It is a project brief. |
| NASA Human Research Program — [5 Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/) | Supplies the five-hazard framework used in the Mission Hazards view and background descriptions. | No. This is explanatory content, not a sensor dataset. |
| NASA Open Science Data Repository — [OSD-575: Inspiration4 serum study](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575), [DOI](https://doi.org/10.26030/mc5d-p710) | Biology Evidence view cites the study and summarizes its sample type, assays, sample count, and collection schedule as research context. | No raw measurements. The prototype shows study metadata only; it does not train on or validate against OSD-575. |
| NASA Science — [OSDR FAQ](https://science.nasa.gov/reference/osdr-faq/) | Informs the source/method explanation about the repository and its data. | No. No records were downloaded through this source. |
| Canadian Space Agency — [Monitoring radiation for astronaut health](https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp) | Background for the radiation-monitoring context and the value of dedicated radiation instruments. | No. No CANS readings or CSA data feed are connected. |
| Canadian Space Agency — [Why do we conduct science experiments in space?](https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp) | Background for the rationale that space research helps study human health and prepare for exploration. | No. No measurements are integrated. |
| NASA OSDR license record for OSD-575 | Dataset page identifies the released study data as CC0; this does not mean ASTRAL redistributes or analyzes the data. | No raw data included in this repository. |

## Demo data and transformations

All individual health readings, check-in history, and habitat readings shown in the prototype are **synthetic**. The illustrative pattern rule compares selected values with a recent personal median and median absolute deviation. It is not clinically validated. No real astronaut medical data, voice recordings, wearable files, or raw research datasets are bundled or uploaded.

## Sources considered but not used as model data

- **WESAD:** not downloaded, trained on, or included. The independent lab wearable dataset is not synchronized with NASA astronaut recordings and does not establish in-flight validity.
- **SUSAS:** not downloaded or included; access and licensing are not assumed.
- **NASA Artemis audio:** not used. Public mission audio is not a labeled stress dataset and is not used to infer mental state.
- **Global Offers** in the event kickoff email (GoDaddy, Google Cloud, Meteomatics, Microsoft, Miro): not required or used in the current prototype. The implementation is a standalone HTML/CSS/JavaScript app with browser-local storage; it has no cloud API or external service dependency.

## AI assistance

Generative AI assisted with feasibility review, interface and submission copy editing, and implementation of the standalone HTML/CSS/JavaScript prototype. The team supplied the core ASTRAL concept and initial five-component framing. Team members should verify every source, inspect the final code, and disclose AI use in the official submission.
