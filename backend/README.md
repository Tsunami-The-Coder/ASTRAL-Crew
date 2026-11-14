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

No fusion rules, medical recommendations, or spacecraft actions are implemented.
Radiation, gravity, medical resources, incident logs, and UI integration remain
future steps. Confirm thresholds, score meanings, missing-data conventions, and
inference time windows with the team before exposing a shared interface.

## Offline verification

```sh
python3 -m unittest backend.test_storage backend.test_simulator -v
```

Tests use disposable databases and do not modify the local demo database.
