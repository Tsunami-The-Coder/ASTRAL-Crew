# Backend — Aarika

## Step 1: local storage

Python's standard-library SQLite is sufficient; no server or package install is
required. From the repository root:

```sh
python3 -m backend.storage
```

This creates `backend/mission.sqlite3` without inserting readings. Existing rows
are preserved. Local database files are excluded by the repository's `.gitignore`.

## Step 2: synthetic snapshot

```sh
python3 -m backend.simulator
```

Each run now appends 12 one-minute snapshots ending at the current UTC time,
then prints the latest stored snapshot. Each contains five crew by default and one cabin
reading. All readings are synthetic illustrative values, not clinical thresholds,
validated personal baselines, or measured astronaut data. CO2 and O2 use percent;
pressure uses kPa, heart rate bpm, HRV RMSSD ms, and EDA microsiemens.

Voice, wearable inference, and assessments are `null` because those pipelines
have not run. Synthetic biometric values are separate from model outputs.
To use a different existing directory for the database:

```sh
python3 -m backend.simulator --database /tmp/astral-demo.sqlite3
```

## Step 3: repeatable scenarios

```sh
python3 -m backend.simulator --scenario co2_rise --seed 42 --steps 12
python3 -m backend.simulator --scenario missing_sensor
python3 -m backend.simulator --scenario faulty_sensor
```

The default scenario is `baseline`. The same seed repeats values, while new runs
append new timestamps. No existing records are deleted. Multiple runs can overlap
in event time; use separate database paths when testing scenarios in isolation.
See [SCENARIOS.md](SCENARIOS.md) for scientific references, units, assumptions,
and the distinction between a scripted trend and a physiological prediction.

## Step 4: read history

```sh
python3 -m backend.history --limit 12
```

This prints the newest 12 stored snapshots in chronological order without
generating readings. An empty initialized database returns `[]`. Optional
`--database`, `--start`, and `--end` select another database and inclusive UTC
time bounds. Example timestamps: `2026-11-14T12:00:00Z`.

Python callers can use `SnapshotStore(path).history(limit=100, start=None,
end=None)`. Results have the same envelope as `latest()`; equal event times use
insertion ID order. Limit must be 1–10000. Snapshot contents remain untouched;
this method does not infer stress, normalize readings, or combine scenarios.
Multiple runs may overlap, so keep separate scenario databases for trend tests.

## Step 5: persistent synthetic crew profiles

The local demo now defaults to **five** members, AST-01 through AST-05. This is
an internal demo override requested by backend's owner; the shared four-person
mission plan and UI/model contract have not changed. Four-member mode remains:

```sh
python3 -m backend.simulator --crew-count 4
```

The simulator registers synthetic profiles in SQLite before saving snapshots.
`SnapshotStore.crew_profiles()` retrieves them. Repeated identical registration
is safe; conflicting profiles are rejected atomically rather than overwriting
existing reference values. Profiles use illustrative reference values, not
learned personal baselines. `backend/crew.py` contains the editable defaults.
The active roster is the snapshot crew list; older snapshots are not rewritten,
and registering a smaller roster does not delete historical profiles.

Run all backend tests with:

```sh
python3 -m unittest discover -s backend -p 'test_*.py' -v
```

## Step 6: configurable CO2 balance

`backend/cabin.py` calculates retained crew-produced CO2 using a simplified
ideal-gas balance. It replaces the former fixed 0.50% endpoint in `co2_rise`.

```sh
python3 -m backend.simulator --scenario co2_rise --steps 120 --cabin-volume-m3 100 --removal-fraction 0
```

Use `--removal-fraction 1` to balance crew production, or `0.5` to remove half
of ongoing production after the scenario's first-quarter change. This fraction
is a demo control, not hardware efficiency. `CabinConfig` also exposes pressure,
temperature, initial concentration, and production rate to Python callers.
Stored `cabin_model` metadata records parameters for reproducibility; future
analysis must use readings, not this fixture ground truth. Crew changes remain
scripted independently and are not symptoms calculated from CO2 concentration.
See SCENARIOS.md for the NASA production-load reference and model limitations.

## Integration details (pending team approval)

`SnapshotStore` stores opaque JSON; `baseline_snapshot()` produces fresh demo
inputs; `save_baseline(store, timestamp)` connects the two. This is an internal
fixture, **not the approved UI/model contract**. Do not wire teammates' pipelines
directly to this fixture layout until shared fields and semantics are agreed.
Future adapters and a service layer can translate approved pipeline results into
storage and dashboard views without coupling UI code to the simulator.

Internal cross-analysis rules and a local analysis/review journal are implemented.
Radiation, gravity, medical resources, UI integration, and model fusion remain
future steps. No medical recommendations or spacecraft actions are implemented. Confirm thresholds, score meanings, missing-data conventions, and
inference time windows with the team before exposing a shared interface.

## Offline verification

```sh
python3 -m unittest backend.test_storage backend.test_simulator -v
```

Tests use disposable databases and do not modify the local demo database.

## Step 7: internal cross-analysis prototype

`backend/cross_analysis.py` compares synthetic biometrics against registered demo
references. It requires at least two changed features per crew member, then at
least two changed crew for a shared-pattern finding. RuleConfig defaults are
engineering test choices, not medical limits: HR +10 bpm, RMSSD -6 ms, EDA +0.4
microsiemens, and CO2 increase +0.01 **percentage points** over the selected window.
All can be replaced by passing a RuleConfig; scientific review remains pending.

Use a fresh scenario database so independent runs do not mix:

```sh
python3 -m backend.simulator --database /tmp/astral-analysis-demo.sqlite3 --scenario co2_rise
python3 -m backend.cross_analysis --database /tmp/astral-analysis-demo.sqlite3
```

Without --save, the inspection command reads existing data and prints a report.
With --save, it appends the report to the mission log (see Step 8). Reusing the database for repeated overlapping runs may
cause the command to reject mixed history. Use a new filename in that case.

Possible findings: SHARED_CREW_CHANGE and POSSIBLE_ENVIRONMENTAL_ASSOCIATION.
A CO2 association needs an earlier usable CO2 reading; otherwise the cause remains
unresolved. The report preserves missing/invalid inputs and unavailable model
outputs. No findings does not establish normal health or a safe cabin. This
prototype checks HR, HRV, EDA, and CO2 only; it is not a complete cabin safety check.

The pure function analyze_snapshot(snapshot, profiles, previous=..., config=...)
expects the internal synthetic fixture layout. Callers must select a prior sample
from the same run; the CLI checks run anchors before comparing. This is not the
approved integration API. No stale-signal timing policy, voice/wearable fusion,
clinical triage, or spacecraft action exists yet. Simulator metadata is never
used to determine diagnostic findings. Future adapters and time-window validation
must be agreed with upstream owners before real pipeline integration.

Existing storage, simulator, and shared contract interfaces are unchanged.


## Step 8: save analysis and human-review history

Use a fresh database filename for each independent scenario:

```sh
python3 -m backend.simulator --database /tmp/astral-log-demo.sqlite3 --scenario co2_rise
python3 -m backend.cross_analysis --database /tmp/astral-log-demo.sqlite3 --save
python3 -m backend.mission_log --database /tmp/astral-log-demo.sqlite3
```

The analysis command prints its saved analysis ID. To append a human review,
replace 1 with that ID and supply your own name and review note:

```sh
python3 -m backend.mission_log --database /tmp/astral-log-demo.sqlite3 --analysis-id 1 --reviewer "Demo reviewer" --decision follow_up --note "Synthetic demo: verify cabin and crew readings."
```

Decisions are `acknowledged`, `dismissed`, or `follow_up`. They are human
statements, not medical clearance or a spacecraft control action. All review
fields are required. Names are supplied locally; this prototype has no identity
authentication. The inspection command initializes journal tables if missing but
never modifies telemetry. Journal entries are append-only through this API; the
SQLite file itself is not tamper-proof. Every --save appends a new analysis,
including repeated analyses of the same snapshots. Deduplication is not provided.

`MissionLog.save_analysis` records the current snapshot ID, optional earlier
snapshot ID, full report, rule configuration/version, and UTC recording time.
`add_review` appends a reviewer, decision, note, and UTC time. `entries(limit=100)`
returns the newest N analyses in insertion order with their review history.
Foreign keys are enabled and nonexistent source IDs/reviews are rejected.
Raw readings and original needs_review flags remain unchanged after review.

Report/source consistency and same-run selection are the analyzer caller's
responsibility; the journal checks source existence and chronology. No report
is accepted as measured data. Schemas remain internal and are not the approved
model/UI handoff. Run all tests with unittest discovery from Step 5.

## Step 9: internal service layer for future dashboard integration

`backend/service.py` wraps existing storage and journal operations. It is an
internal proposal for discussion with Anuj, not an approved shared API. It does
not import a UI framework, run models, or generate demo inputs during reads.

```python
from backend.service import MissionService

service = MissionService('backend/mission.sqlite3')
service.initialize()  # Explicitly create missing tables; inserts no readings.
view = service.overview()
profiles = service.crew_profiles()
crew_points = service.crew_history('AST-01', limit=100)
logs = service.mission_logs(limit=100)
```

`overview()` returns the latest raw snapshot and the most recently recorded
analysis only if it references that exact snapshot ID. Otherwise analysis_status
is `not_run_for_latest_snapshot`, or `no_telemetry` for empty storage. Older
analyses remain available in mission_logs(). Matching IDs do not establish
freshness: per-signal timestamps and an agreed stale-data policy are still needed.
The view preserves nulls and source labels and makes no safety determination.
Read methods require prior initialization and leave data unchanged.

`history(limit=..., start=..., end=...)` delegates to snapshot history.
`crew_history` projects that mission-snapshot window onto a crew ID; its limit
applies before filtering. An absent crew member produces no points rather than
fabricated readings. Registered profiles may include crew not active in the latest
snapshot. Mixed runs remain separate records, not one continuous measured mission;
use isolated scenario databases for demos. Malformed crew lists/duplicate IDs
raise ValueError. Other payload validation remains at the producer boundary.
`record_review(...)` delegates to the journal; it is an explicit write operation.

To print the overview from an existing database:

```sh
python3 -m backend.service --database /tmp/astral-log-demo.sqlite3
```

This command initializes missing tables but never creates crew readings. Final
UI field names, model adapters, concurrent-read consistency, and time policies
require team agreement before integration. No ui/ files or shared contracts were
changed in this step.


## Step 10: per-crew synthetic radiation telemetry

```sh
python3 -m backend.simulator --scenario radiation_rise --radiation-rate-msv-per-day 1.8 --radiation-multiplier 4
```

`backend/radiation.py` supplies configurable rate and piecewise dose integration.
Each crew's radiation object is stored in snapshots and exposed unchanged through
service overview and crew history. Dose is since run start, not since mission day
one or career start. Missing radiation produces nulls. No career threshold is implemented. Step 11 adds demo rate-change findings
alongside the existing biometric/CO2 rules. See SCENARIOS.md for provenance and limitations.


## Step 11: radiation rate-change review rules

Cross-analysis now validates current dose rate and accumulated dose, distinguishes
missing/invalid/unavailable radiation inputs, and compares rates with the earlier
snapshot for the same crew ID. `RuleConfig` adds `radiation_rate_ratio` (default
2) and `radiation_rate_increase_msv_per_day` (default 1). Both a doubling and at
least +1 mSv/day are required by the default **demo** rule. These are engineering
settings, not NASA limits, exposure-clearance criteria, or validated warnings.

```sh
python3 -m backend.simulator --database /tmp/astral-radiation-review.sqlite3 --scenario radiation_rise
python3 -m backend.cross_analysis --database /tmp/astral-radiation-review.sqlite3 --save
python3 -m backend.service --database /tmp/astral-radiation-review.sqlite3
```

Use a fresh filename to avoid mixed runs. `RADIATION_RATE_INCREASE` includes
crew IDs, previous/current rates, and their differences. It can occur without
biometric changes and does not establish a solar storm or clinical effect.
Reports now record rules_version `demo-rules-v2`; older saved reports retain
their original version/configuration. No suitable prior reading means no rate
comparison, not evidence that the current rate is safe. Radiation absent from
older fixture layouts is explicitly reported as missing. No career history is
invented and null career dose is not considered a sensor fault.

The CLI still checks same-run selection. The pure analyzer relies on its caller
to supply an earlier snapshot from the same run. Radiation findings flow through
existing mission-log and service operations without a shared-contract change.


## Step 12: illustrative gravity-adaptation context

Each crew has a `gravity` object, stored and returned with their snapshot:

```sh
python3 -m backend.simulator --microgravity-days 30 --bone-loss-percent-per-30-days 1
```

`backend/gravity.py` supplies a configurable educational bone-density trend,
normalized to 100% at zero exposure days. At 30 days with the demo default, the
illustrative value is 99%. It is not densitometry or a patient prediction. Measured
bone density and cardiovascular assessment remain null. No clinical gravity
assessment or automatic alert is made. Data origin is `simulated_inference`.

Defaults are 142 exposure days and 1% per 30 days; context remains fixed across
minute-scale scenarios. Four/five crew modes are supported. Units, provenance,
parameter assumptions, and domain restrictions are in SCENARIOS.md. All fields
remain internal pending scientific review and shared-contract approval.

## Remaining backend milestones

1. Medical-resource catalog and per-crew review/incident context; clinical content
   must be reviewed and available for lawful offline use.
2. Fuller habitat checks for O2/pressure and appropriate sensor-fault cases;
   scientifically reviewed thresholds and time windows are still needed.
3. Input validation, run identification, stale-data policy, and robust handoffs.
4. Agree shared interfaces and connect voice/wearable outputs and Anuj's UI.
5. Final science review, end-to-end/offline verification, documentation, and PR.

These are scope groups, not five small coding edits. The implementation does not
currently represent a complete integrated five-hazard application.

## Step 13: offline medical resources and simulated incidents

`backend/medical.py` provides an offline JSON catalog and append-only synthetic
incident/note tables. `backend/medical_resources.json` is intentionally empty:
no reviewed checklist content is present in this checkout. `medical_resources()`
returns `availability: no_reviewed_content`; it does not fabricate treatment,
triage, prescriptions, diagnoses, or personal medical histories.

```python
from backend.service import MissionService

service = MissionService('backend/mission.sqlite3')
service.initialize()
resources = service.medical_resources()
# Requires this crew to have been registered by the simulator first.
incident_id = service.record_medical_incident(
    'AST-01', summary='Synthetic demo: crew observation requires review.'
)
service.record_medical_note(
    incident_id, reviewer='Demo reviewer', note='Recorded for human review.'
)
incidents = service.medical_incidents(crew_id='AST-01')
```

Optional snapshot_id links an incident to source telemetry; the snapshot must
exist and include that crew member. Registered crew and snapshot foreign keys
are enforced. Incidents and notes retain UTC recording times. These operations
never alter raw snapshots, rule findings, or previous review notes. No clinical
resolution status is inferred from a note. Summary/notes must contain synthetic
demo content only; do not store real medical records in this prototype database.

Resource schema (internal, pending agreement): resource_id, title, version,
source_url, reuse_terms, review_status (`pending` or `approved`). An approved
entry additionally requires reviewer, reviewed_at (UTC), and offline_content.
Pending entries never expose procedure content. Review labels are team-supplied
metadata, not authenticated clinical certification. All approved content is
bundled text; URLs are provenance references and are not fetched at runtime.
Invalid/missing catalog files raise ValueError explicitly. Eleni must verify
sources/reuse terms, and appropriate review of clinical content remains pending.
Do not change this catalog to approved merely to populate a dashboard.

No medical content was downloaded, no external requests are made at runtime,
and no ui/ files or shared contracts were changed. Run all backend tests using
unittest discovery. This is the medical module's storage/resource foundation,
not a completed autonomous medical support system.


## Step 14: habitat pressure/oxygen review checks

```sh
python3 -m backend.simulator --database /tmp/astral-pressure-review.sqlite3 --scenario pressure_drop
python3 -m backend.cross_analysis --database /tmp/astral-pressure-review.sqlite3 --save
python3 -m backend.service --database /tmp/astral-pressure-review.sqlite3
```

Use a fresh filename per independent run. `oxygen_drop` is a separate scenario.
New findings are CABIN_PRESSURE_DROP and CABIN_OXYGEN_FRACTION_DROP, with previous
and current values and deltas. The report's habitat object includes derived O2
partial pressure (kPa), pressure delta (kPa), and O2 delta (percentage points).
It is stored in analysis logs and passed through the existing service unchanged.
The rules version is now demo-rules-v3; old reports retain their original version.

RuleConfig exposes pressure_decrease_kpa (default 2) and
 o2_decrease_percentage_points (default 1). These are demo comparison settings,
not NASA thresholds or validated fault detection. Findings require a usable prior
sample and can occur without changed crew biometrics. Missing/invalid/unavailable
readings produce input issues rather than a fabricated safe value or confirmed
leak. This is not a complete cabin-safety assessment: stable readings outside a
safe operating range are not detected by delta-only rules. Freshness/time-window
policy, complete composition validation, and scientific review remain pending.
See SCENARIOS.md for curve assumptions and partial-pressure limitations.


## Step 15: run selection and snapshot freshness

This section supersedes the earlier separate-database workaround for newly
created CLI runs and the earlier matching-ID-only service behavior.

Each `python3 -m backend.simulator` invocation now assigns a UUID run_id to its
snapshots and prints it. This is a run identifier, not a crew identifier. The pure
seeded generator remains deterministic; it does not generate random IDs. No old
snapshots are rewritten and no SQL migration is needed: run_id lives in JSON.

`SnapshotStore.history(..., run_id='...')`, service history, and crew_history filter
by run before applying the limit. The cross-analysis CLI defaults to the latest
snapshot's run or accepts `--run-id`. Thus repeated overlapping runs can coexist
without cross-analysis mixing their measurements. Legacy snapshots without IDs
still require the old timestamp-minus-elapsed anchor check. IDs do not prove that
inputs are genuinely synchronized; upstream adapters will need stronger validation.
The pure analyzer rejects different explicit runs and reversed/equal elapsed
comparison times when those fields are present. It remains an internal API.

`MissionService(..., clock=..., max_age_seconds=300)` accepts an injectable aware
clock and a positive freshness interval. **300 seconds is a demo setting**, not
an approved clinical/flight policy. overview() now reports freshness status:
`fresh`, `stale`, `future`, or `unavailable`, with age_seconds and configured limit.
The boundary is inclusive: age 300 is fresh, age 301 stale. Future times are not
accepted as fresh. Historical readings remain visible, but a matching report is
moved from current_analysis to historical_analysis if telemetry is stale/future;
analysis_status is then historical_telemetry. No snapshots are modified/deleted.
This internal service view is version internal-demo-v2. No shared API changed.

Freshness is based only on the enclosing snapshot timestamp. Per-sensor sample
windows, maximum cross-modal skew, hardware clock policy, model versions and score
semantics still need team agreement. Replay timestamps cannot establish genuine
live monitoring, and no fresh result guarantees safety. Read/analysis CLIs can
still analyze historical scenarios intentionally; only the overview distinguishes
historical from current presentation.

Run all checks:

```sh
python3 -m unittest discover -s backend -p 'test_*.py' -q
```

## Step 16: candidate voice/wearable adapters and multimodal analysis

`backend/multimodal.py` composes the existing telemetry rules with adapters and
qualitative model comparison from `fusion/`. Original score semantics, input
origins, model versions, raw JSON-safe outputs, windows, and quality are retained.
There is no combined numeric score or automatic diagnosis. Reports can be saved
through the existing mission log and displayed through the existing service.

See [fusion/INTEGRATION.md](../fusion/INTEGRATION.md) for the explicit adapter
proposal, pinned producer versions, runnable synthetic demo, unavailable/fifth-crew
behavior, and required team-review decisions. No producer source or shared
contract was edited. The standalone cross_analysis CLI remains telemetry-only;
the new wrapper/demo is the model-aware path. When producer modules are not on
this branch, the demo must run in an isolated integration copy containing both
modules; it does not silently merge branches or replace unavailable models.

## Step 17: reviewable JSON handoff for a dashboard

`backend/export.py` reads an existing, service-initialized demo database and
exports overview, raw snapshot history for the latest run, registered profiles,
mission logs/reviews, medical incidents and resource availability. This is a
static internal review artifact, not an approved shared API or a live connection.

```sh
python3 -m backend.export --database /tmp/astral-real-fusion-demo.sqlite3 --replay-clock 2026-11-15T12:00:00Z --output /tmp/astral-ui-handoff.json
```

Use the explicit replay clock only for that synthetic demonstration. Omitting it
uses real UTC and preserves stale/future status; it never restamps old readings.
The output filename must not already exist. This command does not initialize or
modify the source database. Source tables must have been initialized by
MissionService or fusion.demo. Default limit is 100 records per collection and
can be configured using --limit. Logs may include older runs; current roster
comes from overview.snapshot, not every registered profile. Export includes
reviewer names and notes: only synthetic demo content belongs in these artifacts.
The export is not an atomic read under concurrent writes.

Choose and agree the UI destination with Anuj before wiring this view into the
HTML prototype or Streamlit. JSON export alone does not connect browser local
storage to SQLite. Actual model implementations remain on their owner branches;
the prototype was exercised together in an isolated integration copy.
