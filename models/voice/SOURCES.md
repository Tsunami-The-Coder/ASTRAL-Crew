# Sources, datasets and AI disclosure (voice workstream)

## Signal processing and stressed-speech research
| Used for | Reference |
|---|---|
| Teager energy operator | Kaiser JF (1990). On a simple algorithm to calculate the "energy" of a signal. *Proc. IEEE ICASSP*, 381–384. |
| TEO features for stressed speech | Cairns DA, Hansen JHL (1994). Nonlinear analysis and classification of speech under stressed conditions. *J. Acoust. Soc. Am.* 96(6), 3392–3400. |
| TEO-CB-Auto-Env (we implement a simplified version) | Zhou G, Hansen JHL, Kaiser JF (2001). Nonlinear feature based classification of speech under stress. *IEEE Trans. Speech Audio Process.* 9(3), 201–216. |
| Stress raises pitch, vocal effort, changes spectral tilt | Hansen JHL, Patil S (2007). Speech under stress: analysis, modeling and recognition. In *Speaker Classification I*, LNCS 4343, Springer, 108–137. |
| Review of vocal stress indicators | Giddens CL, Barron KW, Byrd-Craven J, Clark KF, Winter AS (2013). Vocal indices of stress: a review. *J. Voice* 27(3), 390.e21–29. |
| SUSAS (research basis only, **not used**: paid LDC licence) | Hansen JHL, Womack BD (1996). Feature analysis and neural network-based classification of speech under stress. *IEEE Trans. Speech Audio Process.* 4(4), 307–313. LDC catalog LDC99S78. |
| MFCC | Davis S, Mermelstein P (1980). Comparison of parametric representations for monosyllabic word recognition. *IEEE Trans. ASSP* 28(4), 357–366. |
| Noise removal in speech pauses | Boll S (1979). Suppression of acoustic noise in speech using spectral subtraction. *IEEE Trans. ASSP* 27(2), 113–120. |

## Datasets
| Dataset | Type | How we use it | Licence |
|---|---|---|---|
| **RAVDESS** speech (Livingstone SR, Russo FA (2018), *PLoS ONE* 13(5): e0196391; https://zenodo.org/records/1188976) | Real but **acted** | Optional training/evaluation of the arousal model (`train.py`). Not downloaded or trained in this commit. | CC BY-NC-SA 4.0 |
| **NASA Artemis Audio Library** (https://www.nasa.gov/artemisaudio) | Real, **unlabelled** | Demonstration only (`artemis_demo.py`). No accuracy claims. | NASA media usage guidelines |
| ASTRAL mission scenarios (`data/scenarios/`, Eleni) | **Synthetic** | Timing and assumed voice levels for `demo.py` | Ours |
| Synthetic speech (`synth.py`) | **Synthetic** | Tests, demos, robustness check | Ours |

No NASA participant data and no real astronaut stress labels were used. No model weights were trained in this commit.

## NASA challenge resources (context for design choices)
- NASA Five Hazards of Human Spaceflight: https://www.nasa.gov/hrp/hazards/ (voice monitoring targets *Isolation & Confinement* and *Distance from Earth*)
- NASA Human Research Program, Individualized Stress Detection task: https://humanresearchroadmap.nasa.gov/Tasks/task.aspx?i=1160 (supports personal baselines over population thresholds)

## AI disclosure
This module was written with AI assistance (Claude, Anthropic), following the team's shared AI prompt and `docs/DATA_CONTRACT.md` rules. All results in `VALIDATION.md` come from scripts that were actually run; nothing was estimated.
