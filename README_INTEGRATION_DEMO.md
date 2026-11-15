# ASTRAL-Crew — local integrated demo

The tested integrated demo has been copied into this Git checkout. These working-tree changes are not committed or pushed yet. The prior preview remains available, and overwritten files were backed up outside this repository. Owner model implementations were copied unchanged.

## Open

Double-click `run_demo.command`, then open http://127.0.0.1:8765/astral-prototype/ . The launcher installs NumPy/SciPy once if needed. Runtime operation uses local assets and requires no internet. The service binds to loopback only.

## Main workflow

1. Open **Crew** and select AST-01 through AST-05.
2. Review the latest timestamped entry. Each member starts with a clearly labelled synthetic reference.
3. Open **Add entry**. Select a voice sample and wearable window; listen to the voice if desired.
4. Click **Generate demo readings** and inspect the draft values.
5. Click **Submit & analyze**. Actual backend stages are displayed, then the entry, analysis and flags are saved locally.
6. Open **Mission control**, choose a cabin scenario and analyze saved crew inputs with the cabin.

Each member has separate entry history and Cognitive, Habitat, Radiation, Gravity and Medical tabs. Habitat is shared. Entry biometrics equal the draft you reviewed. Drafts are single-use, bound to a crew ID and expire after ten minutes. Mission re-analysis does not add pretend member entries. Preset scenarios inside **Advanced scenario playback & export** reset selected scenario inputs; they do not erase entry history.

## Two-minute presentation

- AST-01: generated elevated-arousal voice + elevated wrist window → generate → submit. Show elevated-indicator evidence and a review flag.
- AST-02: repeat elevated inputs.
- Mission control: select rising CO₂ → analyze. Show shared crew changes and a possible environmental association, not a confirmed cause.
- AST-03: calm voice + elevated wrist → submit. Show voice/wearable disagreement.
- AST-04: silence + missing EDA → submit. Show unavailable inputs, not normal scores.
- Optional: play an Artemis or RAVDESS clip and show extracted pitch, MFCC and Teager-energy features. Recorded audio does not produce a paired crew stress score.
- On Flagged findings, record a human review. Export current results from the advanced controls.

## Inputs and scientific limits

| Input | Actual use |
| --- | --- |
| Generated crew/wrist/voice/cabin readings | Synthetic examples processed by the actual models, adapters and rule engine. Their synchronization is scripted. |
| Wearable model | Shipped WESAD-trained logistic research model; no retraining or astronaut validation performed here. Known pulse peak-counting limitations remain. |
| Voice score | Same-speaker personal-baseline deviation; no shipped RAVDESS-trained voice weights. Scores are stress-related arousal indicators, not diagnoses. |
| NASA Artemis II recordings | Two attributed 15-second local WAV excerpts; real quality checks and feature extraction. No verified personal calm baseline or stress labels. |
| RAVDESS recordings | Original Actor 01 calm/neutral/fearful acted recordings, credited under CC BY-NC-SA 4.0. Emotion labels are not physiological stress ground truth. No training or accuracy claim. |
| NASA OSD-575 | Actual serum measurements from four coded research participants, displayed separately in Biology. No fifth NASA participant fabricated. |
| Radiation / gravity | Illustrative synthetic accounting/trends, not wrist-derived measurements or personal risk predictions. |
| Medical support | Per-member module is present; no reviewed emergency checklist content is bundled. |

All five members have telemetry and entries. Current owner models support AST-01 through AST-04 only; AST-05 is explicitly unsupported. There is no live microphone/watch/cabin hardware ingestion. Standalone upload APIs remain internal experiments; uploaded audio is not saved or silently paired with unrelated wearable data.

Sources and Method pages explain the flow, sources and limits. Original/derived recording hashes and transformations are in `submission/astral-prototype/audio/manifest.json` and `audio/ravdess/manifest.json`. Full-length NASA source files remain outside this folder in `/private/tmp`. StressID and SUSAS recordings are not bundled because access/licensing requirements have not been satisfied. NASA attribution does not imply endorsement.

## Backend and UI interfaces

The existing producer interfaces are preserved. These local internal demo routes are not a team-approved shared API:

- `GET /api/mission`: current snapshot/report, reviews and per-member entry history.
- `POST /api/crew/draft`: prepare a synthetic entry without submitting it.
- `POST /api/crew/checkin`: validate a draft, execute pipelines/fusion, save entry and analysis.
- `POST /api/mission/analyze`: combine retained synthetic selections with a cabin scenario.
- `GET /api/progress`: actual operation ID, stages, completion status and elapsed time. UI completion comes from backend state, not timer-based progress.
- `POST /api/reviews`: append a human review bound to the current snapshot and analysis.
- `POST /api/demo/run`: advanced preset scenario.
- `POST /api/lab/test`: standalone engineering sample tests; not the primary entry flow.

Data are stored in `runtime/demo.sqlite3`. Source-bound analyses and human reviews remain separate. No spacecraft systems are controlled.

## Final verification — 15 November 2026

- Runtime environment: `.venv/bin/python -m unittest discover -s backend -p 'test_*.py'`: **100 passed**.
- Validation environment: `python -m unittest models.wearable.test_wearable models.wearable.test_space`: **36 passed**.
- Validation environment: `python -m pytest models/voice -q`: **25 passed, 3 skipped**. Skips require the original research data/scenario fixtures, which are not included.
- Chrome automation with external requests blocked: five member paths; exact draft/submitted values; actual progress completion; elevated, disagreement, missing and unsupported states; NASA and acted audio features; crew/CO₂ association; persistence; review; export; seven mobile pages; reduced motion; interactive Method; Sources. **Passed, zero JavaScript errors.**
- JavaScript and launcher syntax checked separately.

These checks establish software demo behavior, not clinical validity, astronaut accuracy, real sensor synchronization, or production readiness.

## Integration handoff

Task/owner: Aarika backend and integrated demo; UI review with Anuj. Branch/PR: transferred into this checkout as uncommitted working-tree changes; no PR or merge performed. Changes are in backend orchestration/entry storage/server, submission UI/audio, runtime requirements/launcher and this guide. Existing model files remain unchanged; runtime dependencies are NumPy and SciPy only.

This checkout was on an older local main when the files were transferred. Review the working-tree changes on an integration feature branch against current remote main, excluding `.venv`, `runtime`, caches, raw archives and generated outputs. Narrow `.gitignore` exceptions include only the attributed demo WAV assets. Backend and voice workstreams still need reconciliation with main. Then rerun checks from that actual branch and open a PR for teammate review. Remaining scope decisions: four supported model identities versus five displayed members, medical content, optional real hardware, and shared interface approval.

V3 final recheck: all counts above were reproduced on the finalized version. The hazards link, versioned/no-cache assets, stars and nebula layers were checked separately. See `FINAL_CHECKS.json` for the dated verification record.

## Result wording
The dashboard separates three things: analysis results, missing/unsuitable inputs, and optional team review notes. Each flag states the change and one next check. Labels such as “high indicator” refer to unvalidated demo comparison bands; they do not diagnose stress. “No change flagged” refers only to the available inputs. Internal rule codes, model details and saved reports are preserved for inspection.

Active development folder: `/Users/tanushreedas/Documents/project/ASTRAL-Crew`. The downloadable full-project ZIP is a source snapshot, not a Git clone: it contains no repository history, virtual environment, runtime database or private/local files. New edits must still be committed and pushed to update the open PR.

## Result indicators
Badges use text and a symbol as well as colour: coral `!` for both indicators high, amber `⇄` for disagreement or amber `?` for uncertainty, blue `?` for input gaps, muted `—` for unavailable models, and teal `✓` for no change flagged. Older readings use a muted time badge. Individual voice/wearable panels show score meters only for available numeric outputs; missing inputs never receive a filled meter. Voice confidence and movement cautions override an apparently low/high score badge. Colours describe software demo outcomes, not medical severity or fitness for duty.
