# Dataset access and provenance checklist

This file records the current source review for Eleni’s research workstream. Status refers to the ASTRAL prototype in this repository, not to every teammate's separate branch.

| Source | Access, terms, and scientific fit | ASTRAL use/status |
| --- | --- | --- |
| **NASA OSDR OSD-575** — https://osdr.nasa.gov/bio/repo/data/studies/OSD-575 ; DOI https://doi.org/10.26030/mc5d-p710 | NASA OSDR study page and transformed CMP file. The bundled file has 28 serum sample rows for four coded Inspiration4 crew, seven pre/post-flight timepoints around the three-day mission. Study page lists CC0-1.0. | **Used quantitatively** in the separate Biology Evidence view: selected glucose, creatinine, sodium, potassium, and calcium fields with original sample values. No aggregation or model fitting. Not in-flight wearable data and not validation of the personal trend rule. Source CSV/hash and transformation are in `submission/data/README.md`. |
| **WESAD** — UCI DOI https://doi.org/10.24432/C57K5T ; original source https://ubi29.informatik.uni-siegen.de/usi/data_wesad.html | UCI’s current page delegates license terms to the original source. The original WESAD source describes a 15-participant laboratory dataset and permits scientific, non-commercial use with credit. It is not astronaut data; its stress labels are tied to a controlled lab protocol. | **Verified, not used** in ASTRAL’s personal trend rule or as an astronaut classifier. Do not bundle or redistribute the 2.5 GB recordings without checking the governing terms; if a teammate runs a derived-feature demo, cite the paper/source, state the lab domain shift, and do participant-independent evaluation. |
| **SUSAS (LDC99S78)** — https://catalog.ldc.upenn.edu/LDC99S78 ; DOI https://doi.org/10.35111/x4at-ff87 | LDC catalog identifies an LDC non-member user agreement. The agreement limits use to non-commercial education/research/technology development and prohibits redistribution outside the user’s research group unless expressly permitted. Dataset access is not an unrestricted public download. | **Not used.** Do not place SUSAS audio or derived files in a public repository. Use only if the team has lawful access and accepts the agreement; otherwise omit it from the pipeline. It is scripted/simulated stress speech, not astronaut speech. |
| **NASA Artemis Audio Library** — https://www.nasa.gov/artemisaudio/ ; media policy https://www.nasa.gov/nasa-brand-center/images-and-media/ | NASA’s library FAQ says clips may be used under NASA media guidelines, with no separate permission generally required; source attribution is required and the use must not imply NASA endorsement. Some NASA-hosted assets may be third-party copyrighted, so check each chosen clip. | **Not used for stress classification or model training.** Clips are mission speech/audio but are not labeled for stress, synchronized to wearable signals, or clinical ground truth. At most, an explicitly attributed clip could illustrate audio preprocessing; no such clip is currently included in this prototype. |
| **Synthetic mission telemetry** | Generated solely for the interactive demo. | **Used** for fictional daily check-ins, habitat values, and the illustrative pattern-shift scenario. Every screen labels these as synthetic. |

## Reproducible NASA OSDR file details

- Downloaded file: `LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv`; repository copy: `submission/data/OSD-575_CMP_TRANSFORMED.csv`.
- 28 rows × 58 fields, UTF-8 CSV. Sample IDs are retained as coded crew IDs and collection timepoints.
- The chart uses five analyte value fields and the source-provided reference interval. Values are plotted without averaging, normalization, imputation, or classification.
- SHA-256: `5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9`.
- The source lab reference interval is contextual metadata, not a NASA operational limit or astronaut diagnosis threshold.
- The OSDR chart remains separate from all fictional daily check-ins and cabin readings.

## Key sources

- NASA OSDR OSD-575: https://osdr.nasa.gov/bio/repo/data/studies/OSD-575
- NASA OSDR FAQ: https://science.nasa.gov/reference/osdr-faq/
- UCI WESAD dataset record: https://archive.ics.uci.edu/dataset/465/wesad%2Awearable%2Astress%2Aand%2Affect%2Adetection
- Original WESAD dataset source: https://ubi29.informatik.uni-siegen.de/usi/data_wesad.html
- LDC SUSAS catalog and terms: https://catalog.ldc.upenn.edu/LDC99S78
- NASA Artemis Audio Library: https://www.nasa.gov/artemisaudio/
- NASA Media Usage Guidelines: https://www.nasa.gov/nasa-brand-center/images-and-media/
