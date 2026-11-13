# Dataset access and provenance checklist

| Source | Intended use | Status |
| --- | --- | --- |
| WESAD (UCI): https://archive.ics.uci.edu/dataset/465/wesad+wearable+stress+and+affect+detection | Recorded wearable signals and stress labels | Access/license/files to verify |
| SUSAS (LDC): https://catalog.ldc.upenn.edu/LDC99S78 | Stress speech | License/access not guaranteed; find lawful fallback |
| NASA OSDR: https://osdr.nasa.gov/ | Spaceflight scientific evidence and challenge-linked data | Choose specific study and cite accession |
| NASA Artemis audio: https://www.nasa.gov/artemisaudio/ | Aerospace audio processing/demo if suitable | Confirm usable clips and rights; no stress labels |
| Synthetic telemetry | Four crew + cabin + dosimeter + incident scenarios | Generate during event; label synthetic |

Record for each dataset: URL, version, license, download steps, signal types, labels, sample rates, units, limitations, and permitted redistribution.

**Do not claim** that independent wearable and audio datasets are synchronized. Do not train on held-out test participants; prefer participant-independent evaluation where possible.
