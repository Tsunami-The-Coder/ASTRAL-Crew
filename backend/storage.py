"""Internal synthetic snapshot storage; not the shared telemetry API.

Run `python3 -m backend.storage` from the project root to create the local DB.
No model inference, clinical interpretation, or network access occurs here.
"""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path


DEFAULT_DATABASE = Path(__file__).with_name("mission.sqlite3")


class SnapshotStore:
    """Store opaque synthetic JSON objects until the team approves adapters.

    Create one instance per caller; each operation opens/closes its connection.
    Payload fields and nulls are preserved without interpreting their meaning.
    """

    def __init__(self, database_path=DEFAULT_DATABASE):
        self.path = Path(database_path)

    def initialize(self):
        """Create the database/table if absent; preserve existing records."""
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS synthetic_snapshots (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    data_origin TEXT NOT NULL CHECK(data_origin = 'synthetic'),
                    payload_json TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS synthetic_crew_profiles (
                    crew_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL
                )"""
            )

    def register_synthetic_profiles(self, profiles):
        """Add profiles atomically; reject changed existing profiles.

        Re-registering identical profiles is safe. Existing reference values are
        never silently overwritten. This registry is internal and synthetic only.
        A simulation's active roster is its snapshot crew list, not this registry.
        """
        encoded = []
        seen = set()
        for profile in profiles:
            if not isinstance(profile, dict) or profile.get("data_origin") != "synthetic":
                raise ValueError("profiles must be labeled synthetic JSON objects")
            crew_id = profile.get("crew_id")
            if not isinstance(crew_id, str) or not crew_id.strip() or crew_id in seen:
                raise ValueError("profiles require unique nonempty crew_id strings")
            seen.add(crew_id)
            self._validate_json(profile)
            encoded.append((crew_id, json.dumps(profile, allow_nan=False, sort_keys=True)))
        with closing(sqlite3.connect(self.path)) as connection, connection:
            for crew_id, serialized in encoded:
                existing = connection.execute(
                    "SELECT profile_json FROM synthetic_crew_profiles WHERE crew_id = ?",
                    (crew_id,),
                ).fetchone()
                if existing is not None and json.loads(existing[0]) != json.loads(serialized):
                    raise ValueError(f"Profile already exists with different values: {crew_id}")
                connection.execute(
                    "INSERT OR IGNORE INTO synthetic_crew_profiles VALUES (?, ?)",
                    (crew_id, serialized),
                )

    def crew_profiles(self):
        """Return registered synthetic profiles ordered by ID; [] if none."""
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute(
                "SELECT profile_json FROM synthetic_crew_profiles ORDER BY crew_id"
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_synthetic(self, timestamp, payload):
        """Append an internal snapshot and return its ID.

        timestamp must be ISO 8601 with an explicit UTC offset or Z.
        Payload must be a JSON object with string keys and finite numbers.
        No missing fields are supplied and no existing readings are overwritten.
        """
        timestamp = self._utc_timestamp(timestamp)
        if not isinstance(payload, dict):
            raise ValueError("payload must be a JSON object")
        self._validate_json(payload)
        serialized = json.dumps(payload, allow_nan=False)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            cursor = connection.execute(
                """INSERT INTO synthetic_snapshots
                (timestamp, data_origin, payload_json) VALUES (?, 'synthetic', ?)""",
                (timestamp, serialized),
            )
            return cursor.lastrowid

    @staticmethod
    def _utc_timestamp(timestamp):
        if not isinstance(timestamp, str):
            raise ValueError("timestamp must be an ISO 8601 UTC string")
        try:
            parsed = datetime.fromisoformat(timestamp)
        except ValueError as error:
            raise ValueError("timestamp must be an ISO 8601 UTC string") from error
        if parsed.utcoffset() != timedelta(0):
            raise ValueError("timestamp must include UTC timezone (Z or +00:00)")
        return parsed.isoformat(timespec="microseconds").replace("+00:00", "Z")

    @classmethod
    def _validate_json(cls, value):
        if isinstance(value, dict):
            if any(not isinstance(key, str) for key in value):
                raise ValueError("JSON object keys must be strings")
            for item in value.values():
                cls._validate_json(item)
        elif isinstance(value, list):
            for item in value:
                cls._validate_json(item)
        elif value is not None and type(value) not in (str, int, float, bool):
            raise ValueError("payload must contain only JSON values")

    def latest(self):
        """Return the latest snapshot by event time, or None for an empty DB."""
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                """SELECT id, timestamp, data_origin, payload_json
                FROM synthetic_snapshots ORDER BY timestamp DESC, id DESC LIMIT 1"""
            ).fetchone()
        return self._decode(row) if row is not None else None

    def history(self, *, limit=100, start=None, end=None):
        """Return newest matching N records in chronological order.

        UTC start/end are inclusive. Equal timestamps use insertion ID order.
        No payload-specific fields, thresholds, or schema assumptions are used.
        Empty results are []; missing values remain missing. Limit: 1..10000.
        """
        if type(limit) is not int or not 1 <= limit <= 10000:
            raise ValueError("limit must be an integer between 1 and 10000")
        start = self._utc_timestamp(start) if start is not None else None
        end = self._utc_timestamp(end) if end is not None else None
        if start is not None and end is not None and start > end:
            raise ValueError("start must be no later than end")
        clauses, parameters = [], []
        if start is not None:
            clauses.append("timestamp >= ?")
            parameters.append(start)
        if end is not None:
            clauses.append("timestamp <= ?")
            parameters.append(end)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute(
                "SELECT id, timestamp, data_origin, payload_json "
                "FROM synthetic_snapshots" + where +
                " ORDER BY timestamp DESC, id DESC LIMIT ?",
                (*parameters, limit),
            ).fetchall()
        return [self._decode(row) for row in reversed(rows)]

    @staticmethod
    def _decode(row):
        return {
            "id": row[0], "timestamp": row[1], "data_origin": row[2],
            "payload": json.loads(row[3]),
        }


if __name__ == "__main__":
    store = SnapshotStore()
    store.initialize()
    print(f"SQLite database ready: {store.path}")
    print("No demo readings inserted.")
