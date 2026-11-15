"""Timestamped demo member entries and short-lived, server-generated drafts."""
from datetime import datetime, timezone, timedelta
from copy import deepcopy
from uuid import uuid4
import json
import sqlite3
import numpy as np
from backend.simulator import generate_scenario

VOICE_CHOICES={'calm','aroused','silence','artemis-terminator','artemis-closest','ravdess-calm','ravdess-neutral','ravdess-fearful'}
WRIST_CHOICES={'rest','elevated','movement','missing'}

def validate_selection(crew_id, voice, wearable):
    if crew_id not in [f'AST-{i:02}' for i in range(1,6)] or voice not in VOICE_CHOICES or wearable not in WRIST_CHOICES:
        raise ValueError('Choose a valid crew member, voice and wearable sample')

class MemberEntries:
    def __init__(self, engine):
        self.engine=engine
        self.drafts={}
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS demo_member_entries (id INTEGER PRIMARY KEY, crew_id TEXT NOT NULL, timestamp TEXT NOT NULL, payload TEXT NOT NULL)')
            count=db.execute('SELECT COUNT(*) FROM demo_member_entries').fetchone()[0]
        if not count:
            baseline=generate_scenario('baseline',crew_count=5,steps=12)[-1]
            now=datetime.now(timezone.utc).isoformat()
            for index,member in enumerate(baseline['crew']):
                member['biometrics']=engine._wrist_features(1+index*.1)
                self.save(member['crew_id'],now,{'kind':'preloaded','data_origin':'synthetic','member':member,'voice':'calm','wearable':'rest','note':'Preloaded generated reference; not a submitted check-in.'})
    def connect(self):return sqlite3.connect(self.engine.database)
    def save(self,crew_id,timestamp,payload):
        with self.connect() as db:
            return db.execute('INSERT INTO demo_member_entries(crew_id,timestamp,payload) VALUES (?,?,?)',(crew_id,timestamp,json.dumps(payload,allow_nan=False))).lastrowid
    def history(self,crew_id):
        if crew_id not in [f'AST-{i:02}' for i in range(1,6)]:raise ValueError('Invalid crew ID')
        with self.connect() as db:
            rows=db.execute('SELECT id,timestamp,payload FROM demo_member_entries WHERE crew_id=? ORDER BY id DESC LIMIT 20',(crew_id,)).fetchall()
        return [{'id':r[0],'timestamp':r[1],**json.loads(r[2])} for r in rows]
    def draft(self,crew_id,voice,wearable,scenario):
        validate_selection(crew_id,voice,wearable)
        if scenario not in ('baseline','co2_rise','pressure_drop','oxygen_drop','radiation_rise'):raise ValueError('Invalid cabin scenario')
        now=datetime.now(timezone.utc)
        self.drafts={k:v for k,v in self.drafts.items() if datetime.fromisoformat(v['expires_at'])>now}
        if len(self.drafts)>=100:raise ValueError('Too many drafts; wait for older drafts to expire')
        index=int(crew_id[-2:])-1
        member=deepcopy(generate_scenario(scenario,crew_count=5,steps=12)[-1]['crew'][index])
        # Small random variation is a synthetic engineering choice, not a stress model.
        jitter=float(np.random.default_rng().uniform(-.025,.025))
        features=self.engine._wrist_features((2 if wearable in ('elevated','movement') else 1+index*.1)+jitter,moving=wearable=='movement',eda_level=2.8 if wearable=='elevated' else 2.0)
        if wearable=='missing':features['eda_microsiemens']=None
        member['biometrics']=features
        result={'draft_id':str(uuid4()),'crew_id':crew_id,'voice':voice,'wearable':wearable,'scenario':scenario,
                'generated_at':now.isoformat(),'expires_at':(now+timedelta(minutes=10)).isoformat(),'data_origin':'synthetic','member':member}
        self.drafts[result['draft_id']]=result
        return deepcopy(result)
    def get_draft(self,identifier,crew_id):
        result=self.drafts.get(identifier)
        if result is None or result['crew_id']!=crew_id or datetime.fromisoformat(result['expires_at'])<=datetime.now(timezone.utc):
            raise ValueError('Draft missing, expired or belongs to another crew member; generate again')
        return deepcopy(result)
