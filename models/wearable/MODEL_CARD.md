# Wearable model card

## Intended use

Research and demonstration for ASTRAL-Crew's four-person simulated mission.
Not medical diagnosis, mental-health screening, astronaut certification,
causal inference or control of spacecraft systems. AI-assisted implementation.

## Two clearly distinguished modes

1. **Synthetic fixture:** hand-authored logistic coefficients in demo.py. Intended
   solely to exercise interfaces. No training, accuracy or clinical claims.
2. **WESAD research baseline:** standardized logistic regression (C=1,
   balanced class weights, max_iter=2000, random_state=42), fit on original
   wrist recordings. Inert JSON weights support dependency-free inference.

## Dataset and features

WESAD: 15 ground-laboratory participants, not astronauts. Scientific,
non-commercial use with attribution under the original source's conditions.
Wrist BVP 64Hz, EDA 4Hz, ACC 32Hz; synchronized labels at 700Hz.
Target: stress label 2 versus baseline/amusement labels 1 and 3.
Exclude meditation, transition/undefined and ignored labels. Do not reinterpret
meditation or amusement as clinical diagnoses.

Non-overlapping 60-second windows. Keep only windows with one homogeneous
eligible label. Reject invalid signal windows; record counts per participant.

Four features: mean pulse rate, pulse-interval RMSSD, mean EDA, normalized
motion. BVP: third-order 0.5..4Hz Butterworth bandpass, peaks separated by >=16
samples, prominence >=0.25 signal SD; intervals 300..2000ms. Require >=90%
valid intervals and >=20 valid adjacent interval pairs. These are baseline
engineering choices, not NASA-issued parameters or proven quality certification.

Pulse intervals differ from ECG R-R intervals. The shared `hrv_rmssd_ms`
name is retained for compatibility but must be displayed as a pulse-derived
proxy in this model. Exercise, motion artifacts, temperature, sensor placement,
individual variation and laboratory-to-space domain differences can confound results.

## Evaluation design

Leave one participant out (15 folds). Fit preprocessing and classifier only on
the other participants. Fixed features/hyperparameters and 0.5 classification
boundary; no held-out-subject tuning. Do not split overlapping windows across
train/test. No personal baseline adaptation is used for evaluation.

Report per-subject balanced accuracy and macro F1, mean and SD across subjects,
pooled macro F1 and confusion matrix. Refitting all participants for the final
artifact does not make those participants an independent test set for that artifact.
No calibration or external validation has been established. Do not use the score
as clinical certainty, and do not average it with an unrelated voice-model score.

Actual completed run evidence is in VALIDATION.md; do not substitute the original
paper's reported accuracy for this implementation's results.

### Known measurement limitation from the follow-up audit

`signal_audit.py` reproduces double-counting on a synthetic 1 Hz waveform with
a second harmonic: about 120.09 bpm instead of its 60 cycles/min fundamental.
The extracted RMSSD is also affected. A good classification result is not proof
of accurate pulse measurement. Keep v1 experimental pending reference-beat
validation, revised extraction, and a fresh held-out evaluation. No retraining
or spaceflight calibration was performed in this source-review update.

## NASA involvement

NASA resources motivate physiological monitoring, sleep/activity context,
longitudinal measurements and cautious mission interpretation. They did not
supply the learned weights, numerical thresholds, training labels or validation.
Sources and exact feature/design mappings are in SOURCES.md.

No NASA endorsement is implied. Model output cannot establish radiation dose,
bone loss, immune dysfunction, CO2 poisoning, psychiatric disorders or fitness
for duty. Separate appropriate sensors/tests would be needed for those questions.
