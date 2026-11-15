"""Local synthetic analysis and human-review journal; internal API only."""

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from backend.storage import DEFAULT_DATABASE, SnapshotStore


class MissionLog:
    def __init__(self, database_path=DEFAULT_DATABASE):
        self.path = Path(database_path)

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.execute('PRAGMA foreign_keys = ON')
        return connection

    def initialize(self):
        # Add tables to existing snapshot storage; never replace telemetry.
        SnapshotStore(self.path).initialize()
        with closing(self._connect()) as connection, connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS analysis_log (
                id INTEGER PRIMARY KEY,
                recorded_at TEXT NOT NULL,
                snapshot_id INTEGER NOT NULL REFERENCES synthetic_snapshots(id),
                previous_snapshot_id INTEGER REFERENCES synthetic_snapshots(id),
                report_json TEXT NOT NULL
            )''')
            connection.execute('''CREATE TABLE IF NOT EXISTS human_reviews (
                id INTEGER PRIMARY KEY,
                analysis_id INTEGER NOT NULL REFERENCES analysis_log(id),
                recorded_at TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                decision TEXT NOT NULL CHECK(decision IN ('acknowledged','dismissed','follow_up')),
                note TEXT NOT NULL
            )''')

    def save_analysis(self, snapshot_id, report, *, previous_snapshot_id=None):
        """Append an analysis with immutable source IDs and full rule evidence.

        Report must come from the internal analyzer; this journal does not verify
        its clinical correctness or calculate it. Every call creates a new entry.
        """
        if type(snapshot_id) is not int or snapshot_id < 1:
            raise ValueError('snapshot_id must be a positive integer')
        if previous_snapshot_id is not None and (type(previous_snapshot_id) is not int or previous_snapshot_id < 1):
            raise ValueError('previous_snapshot_id must be a positive integer or None')
        if (not isinstance(report, dict) or report.get('data_origin') != 'simulated_inference'
                or not isinstance(report.get('rules_version'), str)
                or not isinstance(report.get('findings'), list)
                or not isinstance(report.get('input_issues'), list)
                or type(report.get('needs_review')) is not bool):
            raise ValueError('expected an internal simulated analysis report')
        SnapshotStore._validate_json(report)
        encoded = json.dumps(report, allow_nan=False)
        with closing(self._connect()) as connection, connection:
            current = connection.execute('SELECT timestamp FROM synthetic_snapshots WHERE id=?', (snapshot_id,)).fetchone()
            if current is None:
                raise ValueError('source snapshot does not exist')
            if previous_snapshot_id is not None:
                previous = connection.execute('SELECT timestamp FROM synthetic_snapshots WHERE id=?', (previous_snapshot_id,)).fetchone()
                if previous is None or previous[0] >= current[0]:
                    raise ValueError('comparison snapshot must exist and be strictly earlier')
            cursor = connection.execute('''INSERT INTO analysis_log
                (recorded_at,snapshot_id,previous_snapshot_id,report_json) VALUES (?,?,?,?)''',
                (datetime.now(timezone.utc).isoformat(), snapshot_id, previous_snapshot_id, encoded))
            return cursor.lastrowid

    def add_review(self, analysis_id, *, reviewer, decision, note):
        """Append a human statement; identity is supplied, not authenticated.

        Acknowledgment/dismissal does not establish safe conditions or change raw
        readings or original needs_review. Later reviews preserve earlier notes.
        """
        if type(analysis_id) is not int or analysis_id < 1:
            raise ValueError('analysis_id must be a positive integer')
        if decision not in ('acknowledged', 'dismissed', 'follow_up'):
            raise ValueError('decision must be acknowledged, dismissed, or follow_up')
        if any(not isinstance(value, str) or not value.strip() for value in (reviewer, note)):
            raise ValueError('reviewer and note must be nonempty strings')
        with closing(self._connect()) as connection, connection:
            if connection.execute('SELECT id FROM analysis_log WHERE id=?', (analysis_id,)).fetchone() is None:
                raise ValueError('analysis does not exist')
            cursor = connection.execute('''INSERT INTO human_reviews
                (analysis_id,recorded_at,reviewer,decision,note) VALUES (?,?,?,?,?)''',
                (analysis_id, datetime.now(timezone.utc).isoformat(), reviewer.strip(), decision, note.strip()))
            return cursor.lastrowid

    def entries(self, limit=100):
        """Newest N analyses, chronological insertion order, with all reviews."""
        if type(limit) is not int or not 1 <= limit <= 10000:
            raise ValueError('limit must be an integer between 1 and 10000')
        with closing(self._connect()) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute('SELECT * FROM analysis_log ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
            entries = []
            for row in reversed(rows):
                entry = dict(row)
                entry['report'] = json.loads(entry.pop('report_json'))
                entry['reviews'] = [dict(review) for review in connection.execute(
                    'SELECT * FROM human_reviews WHERE analysis_id=? ORDER BY id', (row['id'],))]
                entries.append(entry)
        return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--analysis-id', type=int)
    parser.add_argument('--reviewer')
    parser.add_argument('--decision', choices=('acknowledged','dismissed','follow_up'))
    parser.add_argument('--note')
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error('Database missing; generate a scenario first.')
    review_requested = any(value is not None for value in (args.analysis_id,args.reviewer,args.decision,args.note))
    if review_requested and any(value is None for value in (args.analysis_id,args.reviewer,args.decision,args.note)):
        parser.error('A review requires --analysis-id, --reviewer, --decision, and --note together.')
    log = MissionLog(args.database)
    try:
        log.initialize()
        if review_requested:
            log.add_review(args.analysis_id,reviewer=args.reviewer,decision=args.decision,note=args.note)
        print(json.dumps(log.entries(args.limit),indent=2))
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
