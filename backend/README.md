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
