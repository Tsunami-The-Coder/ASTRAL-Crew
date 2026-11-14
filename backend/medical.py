"""Offline resource catalog and simulated incident journal, not medical triage."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from backend.storage import DEFAULT_DATABASE, SnapshotStore

CATALOG_PATH = Path(__file__).with_name('medical_resources.json')


def resource_catalog(path=CATALOG_PATH):
    """Load bundled JSON only; no URL fetching. Approved content needs review metadata.

    Review metadata is supplied by the team, not authentication or certification.
    Pending entries expose metadata but no usable procedure. Catalog errors raise
    ValueError instead of returning fabricated clinical guidance.
    """
    try:
        catalog = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise ValueError('Offline medical catalog is missing or invalid') from error
    if (not isinstance(catalog, dict) or not isinstance(catalog.get('catalog_version'),str)
            or not isinstance(catalog.get('resources'),list)):
        raise ValueError('Invalid catalog structure')
    seen, resources = set(), []
    for resource in catalog['resources']:
        if not isinstance(resource,dict):
            raise ValueError('Resource must be an object')
        required = ('resource_id','title','version','source_url','reuse_terms','review_status')
        if any(not isinstance(resource.get(key),str) or not resource[key].strip() for key in required):
            raise ValueError('Resource metadata is incomplete')
        if resource['resource_id'] in seen:
            raise ValueError('Duplicate resource ID')
        seen.add(resource['resource_id'])
        if resource['review_status'] not in ('pending','approved'):
            raise ValueError('Unknown resource review status')
        item = dict(resource)
        if item['review_status'] == 'approved':
            for key in ('reviewer','reviewed_at','offline_content'):
                if not isinstance(item.get(key),str) or not item[key].strip():
                    raise ValueError('Approved resource requires review evidence and offline content')
            SnapshotStore._utc_timestamp(item['reviewed_at'])
        else:
            item['offline_content'] = None
        resources.append(item)
    return {'catalog_version':catalog['catalog_version'],'resources':resources,
            'availability':'available' if any(r['review_status']=='approved' for r in resources)
                           else 'no_reviewed_content',
            'limitations':'Human-reviewed demo resources only; no automatic diagnosis or treatment.'}


class MedicalStore:
    def __init__(self,database_path=DEFAULT_DATABASE):
        self.path = Path(database_path)

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.execute('PRAGMA foreign_keys = ON')
        return connection

    def initialize(self):
        SnapshotStore(self.path).initialize()
        with closing(self._connect()) as connection,connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS medical_incidents (
                id INTEGER PRIMARY KEY,
                crew_id TEXT NOT NULL REFERENCES synthetic_crew_profiles(crew_id),
                recorded_at TEXT NOT NULL,
                summary TEXT NOT NULL,
                snapshot_id INTEGER REFERENCES synthetic_snapshots(id),
                data_origin TEXT NOT NULL CHECK(data_origin='synthetic')
            )''')
            connection.execute('''CREATE TABLE IF NOT EXISTS medical_incident_notes (
                id INTEGER PRIMARY KEY,
                incident_id INTEGER NOT NULL REFERENCES medical_incidents(id),
                recorded_at TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                note TEXT NOT NULL
            )''')

    def create_incident(self,crew_id,*,summary,snapshot_id=None):
        """Append a simulated incident for registered crew; no diagnosis inferred."""
        if any(not isinstance(value,str) or not value.strip() for value in (crew_id,summary)):
            raise ValueError('crew_id and summary must be nonempty strings')
        if snapshot_id is not None and (type(snapshot_id) is not int or snapshot_id < 1):
            raise ValueError('snapshot_id must be a positive integer or None')
        with closing(self._connect()) as connection,connection:
            if connection.execute('SELECT crew_id FROM synthetic_crew_profiles WHERE crew_id=?',(crew_id,)).fetchone() is None:
                raise ValueError('Crew profile is not registered')
            if snapshot_id is not None:
                row = connection.execute('SELECT payload_json FROM synthetic_snapshots WHERE id=?',(snapshot_id,)).fetchone()
                if row is None:
                    raise ValueError('Source snapshot does not exist')
                crew = json.loads(row[0]).get('crew',[])
                if not isinstance(crew,list) or not any(isinstance(c,dict) and c.get('crew_id')==crew_id for c in crew):
                    raise ValueError('Crew member is absent from source snapshot')
            cursor = connection.execute('''INSERT INTO medical_incidents
                (crew_id,recorded_at,summary,snapshot_id,data_origin) VALUES (?,?,?,?,'synthetic')''',
                (crew_id,datetime.now(timezone.utc).isoformat(),summary.strip(),snapshot_id))
            return cursor.lastrowid

    def add_note(self,incident_id,*,reviewer,note):
        if type(incident_id) is not int or incident_id < 1:
            raise ValueError('incident_id must be a positive integer')
        if any(not isinstance(value,str) or not value.strip() for value in (reviewer,note)):
            raise ValueError('reviewer and note must be nonempty strings')
        with closing(self._connect()) as connection,connection:
            if connection.execute('SELECT id FROM medical_incidents WHERE id=?',(incident_id,)).fetchone() is None:
                raise ValueError('Incident does not exist')
            cursor=connection.execute('''INSERT INTO medical_incident_notes
                (incident_id,recorded_at,reviewer,note) VALUES (?,?,?,?)''',
                (incident_id,datetime.now(timezone.utc).isoformat(),reviewer.strip(),note.strip()))
            return cursor.lastrowid

    def incidents(self,*,crew_id=None,limit=100):
        if type(limit) is not int or not 1 <= limit <= 10000:
            raise ValueError('limit must be an integer between 1 and 10000')
        if crew_id is not None and (not isinstance(crew_id,str) or not crew_id.strip()):
            raise ValueError('crew_id must be a nonempty string or None')
        with closing(self._connect()) as connection:
            connection.row_factory=sqlite3.Row
            where=' WHERE crew_id=?' if crew_id is not None else ''
            params=(crew_id,limit) if crew_id is not None else (limit,)
            rows=connection.execute('SELECT * FROM medical_incidents'+where+' ORDER BY id DESC LIMIT ?',params).fetchall()
            result=[]
            for row in reversed(rows):
                entry=dict(row)
                entry['notes']=[dict(note) for note in connection.execute(
                    'SELECT * FROM medical_incident_notes WHERE incident_id=? ORDER BY id',(row['id'],))]
                result.append(entry)
        return result
