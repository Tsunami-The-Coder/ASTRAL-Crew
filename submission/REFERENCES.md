# ASTRAL Crew — sources, use, and provenance

This map separates real study measurements from contextual references and synthetic demonstration values.

| Source | Use in ASTRAL | Data use |
| --- | --- | --- |
| NASA Space Apps 2026 challenge — [Create Health Monitoring Software for Astronauts on Space Missions](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/) | Defines the self-assessment workflow, indicator examples, user guidance, and design objective. | Requirements brief; no data. |
| NASA Human Research Program — [5 Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/) | Structures the Mission Hazards view and background explanations. | Public explanatory resource; no sensor dataset. |
| NASA OSDR — [OSD-575 Inspiration4 serum study](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575), [DOI 10.26030/mc5d-p710](https://doi.org/10.26030/mc5d-p710) | Biology Evidence view includes a selectable chart of five analytes from the transformed comprehensive metabolic panel (CMP), by four pseudonymous crew codes and seven sample timepoints. | **Actual public source data used.** File included under `data/OSD-575_CMP_TRANSFORMED.csv`. License on study page: CC0-1.0. SHA-256: `5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9`. |
| NASA Science — [OSDR FAQ](https://science.nasa.gov/reference/osdr-faq/) | Informs repository/method description and download citation. | Repository guidance; not a separate dataset. |
| Canadian Space Agency — [Monitoring radiation for astronaut health](https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp) | Background for radiation-monitoring context and the role of dedicated instruments. | No CANS readings or CSA data feed. |
| Canadian Space Agency — [Why conduct science experiments in space?](https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp) | Background rationale for human research in space. | No measurements integrated. |
| UCI / original WESAD source — [dataset record](https://archive.ics.uci.edu/dataset/465/wesad%2Awearable%2Astress%2Aand%2Affect%2Adetection), [original site](https://ubi29.informatik.uni-siegen.de/usi/data_wesad.html), [2018 paper](https://doi.org/10.1145/3242969.3242985) | Source and terms review for the separate wearable model. Original source describes a 15-person laboratory study and scientific, non-commercial use with attribution. | The browser's separate WESAD sandbox applies the team's repository model coefficients to an explicitly synthetic 60-second feature vector. No raw dataset is redistributed. The uncalibrated output is not astronaut or clinical validation; the model card documents a pulse-peak double-counting limitation. |
| Linguistic Data Consortium — [SUSAS LDC99S78](https://catalog.ldc.upenn.edu/LDC99S78), [non-member agreement](https://catalog.ldc.upenn.edu/license/ldc-non-members-agreement.pdf) | Access and redistribution review only. The agreement limits use and does not permit redistribution outside the research group unless allowed. | Not used; no recordings or derived files included. |
| NASA — [Artemis Audio Library](https://www.nasa.gov/artemisaudio/), [media usage guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/) | Suitability and use-policy review only. Public clips can be used under NASA's media guidelines with attribution; check each asset for third-party restrictions. | Not used for stress labeling, training, or validation. NASA mission speech has no stress ground truth and is not synchronized with wearable datasets. |

## NASA dataset fields and transformation

- Source file: `LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv` (downloaded from the OSDR OSD-575 study page; the repository copy is renamed `OSD-575_CMP_TRANSFORMED.csv`).
- The source file has 28 sample rows and 58 columns. The page chart uses the values and source reference interval for serum glucose, creatinine, sodium, potassium, and calcium.
- Sample names are parsed to preserve coded crew ID (C001–C004) and collection timepoint (L−92, L−44, L−3, R+1, R+45, R+82, R+194). Values are plotted individually; no averaging, imputation, modeling, or normalization is applied.
- The source lab reference interval appears as a shaded band, only for data context. It is not described as a NASA operational limit, clinical threshold for astronauts, or diagnosis.
- No raw values are used to train or validate the personal trend rule. This serum study is separate from the synthetic daily wearable-style demo.

## Synthetic data and tools not used

All personal check-in history, change scenarios, and habitat values are synthetic. No real user health information is included. The browser prototype runs the team's WESAD-derived model only in a separate sandbox using synthetic feature inputs; it is disconnected from daily check-in values and sensors. No raw WESAD data are included. The original source limits WESAD use to scientific non-commercial purposes with credit. SUSAS was reviewed but not used; its LDC agreement restricts use and redistribution. Artemis clips were reviewed but not used for stress labels or training: they have no stress ground truth, and use requires compliance with NASA media guidelines and clip-specific third-party restrictions. See [`SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md) for team submission tasks and [`docs/DATA_SOURCES.md`](../docs/DATA_SOURCES.md) for the detailed access review. The optional hackathon Global Offers (GoDaddy, Google Cloud, Meteomatics, Microsoft, and Miro) were not used; the current app has no third-party API or cloud dependency.

## AI assistance

Generative AI assisted with feasibility review, interface and submission copy editing, code implementation, and demo-deck preparation. The team supplied the core ASTRAL concept and initial five-component framing. Team members should verify claims and data handling and disclose AI use in the official submission.
