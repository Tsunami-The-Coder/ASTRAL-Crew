"""Internal dashboard-facing facade; pending agreement with the UI owner."""

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from math import isfinite

from backend.mission_log import MissionLog
from backend.medical import MedicalStore, resource_catalog
from backend.storage import DEFAULT_DATABASE, SnapshotStore


class MissionService:
    """Keep callers independent of SQL and simulator generation.

    initialize() explicitly creates missing local tables. Read methods never run
    inference, seed data, or silently present an older report as current.
    This internal view does not establish that readings are fresh or safe.
    """

    def __init__(self, database_path=DEFAULT_DATABASE, *, clock=None, max_age_seconds=300):
        if type(max_age_seconds) not in (int, float) or not isfinite(max_age_seconds) or max_age_seconds <= 0:
            raise ValueError('max_age_seconds must be finite and positive')
        self.clock = clock if clock is not None else lambda: datetime.now(timezone.utc)
        self.max_age_seconds = max_age_seconds
        self.store = SnapshotStore(database_path)
        self.log = MissionLog(database_path)
        self.medical = MedicalStore(database_path)

    def initialize(self):
        self.log.initialize()
        self.medical.initialize()

    def overview(self):
        snapshot = self.store.latest()
        logged = self.log.entries(limit=1)
        latest_analysis = logged[0] if logged else None
        matches = (snapshot is not None and latest_analysis is not None
                   and latest_analysis['snapshot_id'] == snapshot['id'])
        freshness = {'status': 'unavailable', 'age_seconds': None,
                     'max_age_seconds': self.max_age_seconds}
        if snapshot is not None:
            now = self.clock()
            if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
                raise ValueError('clock must return a timezone-aware datetime')
            timestamp = datetime.fromisoformat(SnapshotStore._utc_timestamp(snapshot['timestamp']))
            age = (now - timestamp).total_seconds()
            freshness.update(age_seconds=age, status=(
                'future' if age < 0 else 'stale' if age > self.max_age_seconds else 'fresh'))
        usable = matches and freshness['status'] == 'fresh'
        return {
            'view_version': 'internal-demo-v2',
            'freshness': freshness,
            'historical_analysis': latest_analysis if matches and not usable else None,
            'data_origin': 'synthetic',
            'snapshot': snapshot,
            'current_analysis': latest_analysis if usable else None,
            'analysis_status': ('available' if usable else
                                'historical_telemetry' if matches else
                                'not_run_for_latest_snapshot' if snapshot else 'no_telemetry'),
            'limitations': [
                'Internal demo view; UI/model contract approval is pending.',
                'Freshness uses snapshot time only; per-signal freshness remains unverified.',
                'Missing model outputs remain null; no diagnosis is provided.',
            ],
        }

    def history(self, *, limit=100, start=None, end=None, run_id=None):
        return self.store.history(limit=limit, start=start, end=end, run_id=run_id)

    def crew_history(self, crew_id, *, limit=100, start=None, end=None, run_id=None):
        """Project a mission history window onto one crew ID.

        Limit selects mission snapshots BEFORE filtering. Samples where that
        crew is absent are omitted, never filled from another crew or prior run.
        Empty/unknown crew returns []; the caller can consult crew_profiles().
        """
        if not isinstance(crew_id, str) or not crew_id.strip():
            raise ValueError('crew_id must be a nonempty string')
        result = []
        for row in self.history(limit=limit, start=start, end=end, run_id=run_id):
            crew = row['payload'].get('crew')
            if not isinstance(crew, list):
                raise ValueError('stored snapshot has no valid crew list')
            matches = [member for member in crew
                       if isinstance(member, dict) and member.get('crew_id') == crew_id]
            if len(matches) > 1:
                raise ValueError('stored snapshot contains duplicate crew IDs')
            if matches:
                result.append({'snapshot_id': row['id'], 'timestamp': row['timestamp'],
                               'data_origin': row['data_origin'], 'crew': matches[0]})
        return result

    def crew_profiles(self):
        return self.store.crew_profiles()

    def mission_logs(self, limit=100):
        return self.log.entries(limit)

    def medical_resources(self):
        return resource_catalog()

    def medical_incidents(self, *, crew_id=None, limit=100):
        return self.medical.incidents(crew_id=crew_id, limit=limit)

    def record_medical_incident(self, crew_id, *, summary, snapshot_id=None):
        return self.medical.create_incident(crew_id, summary=summary, snapshot_id=snapshot_id)

    def record_medical_note(self, incident_id, *, reviewer, note):
        return self.medical.add_note(incident_id, reviewer=reviewer, note=note)

    def record_review(self, analysis_id, *, reviewer, decision, note):
        return self.log.add_review(analysis_id, reviewer=reviewer, decision=decision, note=note)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error('Database missing; generate a scenario first.')
    service = MissionService(args.database)
    service.initialize()
    print(json.dumps(service.overview(), indent=2))


if __name__ == '__main__':
    main()
