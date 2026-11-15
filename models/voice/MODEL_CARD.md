# Model card: ASTRAL-Crew voice stress indicator (`personal_baseline_v1`)

## Purpose
Flags when an astronaut's voice deviates from **their own** calm baseline in the directions associated with stress and arousal. The output is one input to the integration lead's multimodal fusion. It is a **research indicator, not a diagnosis**, and it is never used alone to trigger actions.

## Inputs and outputs
- **Input:** one utterance of mono audio (any sample rate, resampled to 16 kHz), `crew_id` (`AST-01`…`AST-05`), timestamp.
- **Output:** the DATA_CONTRACT record `{crew_id, timestamp, stress_score, confidence, source:"voice", data_type}`, or no record when there is no usable speech or the baseline is still being enrolled. Optional `details` (explanation, flags, features) are kept separate so the contract is unchanged.

## Method
1. **Pre-processing:** 4th-order zero-phase Butterworth band-pass 300–3400 Hz (removes cabin fan hum), 25 ms frames / 10 ms hop, energy VAD, spectral subtraction of the noise measured in speech pauses.
2. **Features (24):** pitch (median, SD, 5–95 % range, frame-to-frame jitter proxy), loudness (mean, SD, shimmer proxy), spectral centroid, energy above 1 kHz, Teager energy (log mean), simplified TEO-CB-Auto-Env over 5 bands, voiced fraction, MFCC 1–12 means.
3. **Personal baseline:** mean and SD of each feature over ≥ 5 calm enrollment utterances (up to the most recent 60), with SD floors.
4. **Rule score:** z-scores against the baseline → signed weighted mean of 9 arousal-related features → logistic mapping (1 SD weighted deviation = 0.5).
5. **Optional learned score:** logistic regression on the same z-scores, trained with `train.py` on RAVDESS (per-actor neutral baseline, actor-independent folds). If `model.json` exists, the final score is the average of rule and model. **No `model.json` is shipped yet.**
6. **Confidence:** heuristic from speech duration, SNR, clipping, baseline size and voice-profile mismatch. It is not a calibrated probability.

### Team assumptions (not fitted, not validated on humans)
Feature weights and directions in `scoring.AROUSAL_WEIGHTS`, the logistic slope/centre, SD floors in `baseline.STD_FLOOR`, and the confidence factors. Directions come from the literature in `SOURCES.md`; magnitudes are our choice.

## Training data
None in this commit. The design needs no stress labels, because it scores deviation from the person's own baseline (recommended in `research/SCIENCE_REVIEW.md` item 1). `train.py` is ready for RAVDESS, which is **acted** emotion: report it as "acted high-arousal speech as a stress proxy".

## Evaluation
See `VALIDATION.md`. Everything measured so far uses **synthetic** speech: it tests the code, the filter and the scoring logic, not human physiology. There is **no accuracy figure for real stress**.

## Known limitations
- **Arousal ≠ stress.** Excitement, laughter, shouting over noise or a heated but harmless discussion also raise arousal. Fusion must combine voice with wearables and context.
- **Wrong `crew_id` = wrong baseline.** A different speaker scored against someone else's baseline looks "aroused". The `voice_profile_mismatch` flag catches only large timbre differences.
- **Masking:** backend lead raised astronauts who act calm under stress. Trained crew may control pitch and loudness; TEO/jitter features are less voluntary, but we have not measured whether they reveal masked stress. This is an open question, not a feature.
- **Noise:** at 0 dB SNR, calm speech triggers ≥ 0.6 in 16 % of synthetic cases (see `VALIDATION.md`). Confidence is halved below 5 dB SNR so fusion trusts it less.
- **Microgravity** changes the voice (fluid shift, upper-airway congestion). This is another reason baselines must be enrolled **in flight**, not on the ground.
- **Short clips** (< 1 s of speech) are rejected; 1–3 s get reduced confidence.
- Pitch tracking works for roughly 75–400 Hz voices. Whispering has no pitch and returns no record.

## Ethical use
Indicators for crew self-monitoring and the crew medical officer, with the crew in the loop. No automatic lock-outs or task removal from voice alone (`research/SCIENCE_REVIEW.md` item 7). Audio should stay on board; only scores and features need to be stored.

