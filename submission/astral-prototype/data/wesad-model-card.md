# WESAD research model — browser demo notes

This page documents the experimental model panel in the ASTRAL Crew demo.

## What the demo runs

The panel applies the team's repository logistic-regression coefficients to four user-editable values representing a synthetic 60-second wrist-feature summary: mean pulse rate, pulse-interval RMSSD proxy, mean electrodermal activity, and normalized motion. The initial values are synthetic copies of the training-feature means. No raw WESAD recording or live wearable signal is loaded in the browser.

The model was developed from WESAD, a controlled laboratory dataset with 15 participants. It is not astronaut data. Its 0–1 output is an uncalibrated model score, not a clinical probability, diagnosis, validated stress state, or fitness-for-duty assessment. It has no validated decision threshold and is not connected to the daily check-in, NASA OSDR data, or spacecraft sensors.

## Important measurement limitation

The team's model card reports a pulse-detection audit in which a synthetic waveform with a second harmonic led to double-counted peaks (about 120 bpm instead of a 60 cycles/min fundamental), affecting the pulse-derived RMSSD feature. The score is therefore an experimental software demonstration only. Motion can also confound the signals. The demo's motion caution is a software rule, not a NASA limit.

## Sources

- WESAD dataset: https://doi.org/10.24432/C57K5T
- Original WESAD source and use conditions: https://ubi29.informatik.uni-siegen.de/usi/data_wesad.html
- Team's full model card and validation records: https://github.com/Tsunami-The-Coder/ASTRAL-Crew/tree/main/models/wearable

No NASA or CSA endorsement is implied.
