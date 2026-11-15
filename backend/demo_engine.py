"""Local demonstration orchestration on synthetic audio and wrist waveforms."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import numpy as np
import time

from backend.multimodal import analyze_multimodal
from backend.service import MissionService
from backend.simulator import generate_scenario
from backend.export import export_bundle
from integration.adapters import adapt_voice, adapt_wearable
from models.voice import VoiceStressEstimator
from models.voice import synth
from models.wearable import assess, load_model
from models.wearable.signals import extract_window

SCENARIOS = {
    'baseline': 'Baseline crew',
    'co2_rise': 'Shared changes + CO₂ rise',
    'disagreement': 'Voice / wearable disagreement',
    'missing_sensor': 'Missing signals',
    'faulty_sensor': 'Invalid sensor reading',
    'exercise': 'Movement caution',
    'radiation_rise': 'Radiation rate rise',
    'pressure_drop': 'Cabin pressure drop',
    'oxygen_drop': 'Cabin oxygen drop',
}


class DemoEngine:
    """No training, downloads, raw human recordings, or spacecraft control."""
    def __init__(self, database, model_path):
        self.database = Path(database)
        self.service = MissionService(self.database)
        self.service.initialize()
        self.model = load_model(model_path)
        self.voice = VoiceStressEstimator(baseline_path=None, model_path=None, auto_enroll=False)
        for i, (crew, profile) in enumerate(synth.SPEAKERS.items()):
            clips = [synth.utterance(profile, 3, seed=i * 100 + n) for n in range(10)]
            self.voice.enroll(crew, clips, data_type='synthetic')
        self.profiles = []
        for index in range(5):
            features = self._wrist_features(1 + index * .1)
            self.profiles.append({
                'crew_id': f'AST-{index + 1:02}', 'data_origin': 'synthetic',
                'profile_version': 'integration-wrist-reference-v1',
                'baseline': features,
                'limitations': 'Reference extracted from generated waveforms; not a clinical or measured personal baseline.',
            })
        self.service.store.register_synthetic_profiles(self.profiles)
        self.progress = None
        self.last_case = None
        latest = self.service.store.latest()
        self.checkins = latest['payload'].get('crew_checkins', {}) if latest else {}
        from backend.member_entries import MemberEntries
        self.entries = MemberEntries(self)

    @staticmethod
    def _wrist_features(pulse_hz, moving=False, eda_level=2.0):
        bvp = np.sin(2 * np.pi * pulse_hz * np.arange(3840) / 64)
        eda = np.full(240, eda_level)
        acc = np.tile([0., 0., 64.], (1920, 1))
        if moving:
            acc[:, 0] = 64 * .25 * np.sin(2 * np.pi * np.arange(1920) / 32)
        return extract_window(bvp, eda, acc)

    def _stage(self, stage):
        names = ['validation', 'features', 'analysis', 'save']
        index = names.index(stage)
        self.progress = {**self.progress, 'stage':stage, 'status':'running',
                         'steps':{name:'complete' if i < index else 'running' if i == index else 'pending'
                                  for i,name in enumerate(names)},
                         'elapsed_ms':round((time.monotonic()-self._started)*1000)}

    def run(self, case, *, checkins=None, operation_id=None):
        if operation_id is not None and (not isinstance(operation_id,str) or not 1 <= len(operation_id) <= 80):
            raise ValueError('Invalid operation identifier')
        self._started = time.monotonic()
        self.progress = {'operation_id':operation_id or str(uuid4())}
        self._stage('validation')
        if case not in SCENARIOS:
            raise ValueError('Unknown demonstration scenario')
        selections = deepcopy(checkins) if checkins is not None else {}
        for crew_id, selection in selections.items():
            if crew_id not in [f'AST-{i:02}' for i in range(1,6)] or not isinstance(selection, dict):
                raise ValueError('Invalid check-in crew')
            from backend.member_entries import validate_selection
            validate_selection(crew_id, selection.get('voice'), selection.get('wearable'))
        self._stage('features')
        base = 'baseline' if case in ('disagreement', 'exercise') else case
        samples = generate_scenario(base, crew_count=5, steps=12)
        run_id = str(uuid4())
        for step, sample in enumerate(samples):
            sample['run_id'] = run_id
            sample['scenario'] = case
            sample['crew_checkins'] = deepcopy(selections)
            sample['limitations'] = [
                'Synthetic local demo, not live crew measurements.',
                'Raw features and model indicators do not establish a cause or diagnosis.',
            ]
            progress = max(0, (step / (len(samples) - 1) - .25) / .75)
            for index, member in enumerate(sample['crew']):
                selection = selections.get(member['crew_id'])
                base_hz = 1 + index * .1
                elevated = (case == 'co2_rise' and index < 3) or (case == 'disagreement' and index == 2) or (case == 'exercise' and index == 0)
                if checkins is not None:
                    elevated = bool(selection and selection['wearable'] in ('elevated','movement'))
                hz = base_hz + (2 - base_hz) * progress if elevated else base_hz
                # Deterministic illustrative window-to-window variation; not measured physiology.
                hz += .035 * np.sin(step * 1.3 + index)
                features = self._wrist_features(hz, moving=((case == 'exercise' and index == 0 and checkins is None) or bool(selection and selection['wearable']=='movement')) and progress > 0,
                                                eda_level=2.0 + .8 * progress if elevated else 2.0)
                if selection and selection['wearable']=='missing' and step >= len(samples)//2:
                    features['eda_microsiemens'] = None
                if case == 'missing_sensor' and index == 0 and step >= len(samples) // 2:
                    features['eda_microsiemens'] = None
                if case == 'faulty_sensor' and index == 0 and step >= len(samples) // 2:
                    features['heart_rate_bpm'] = -10
                if step == len(samples)-1 and selection and 'draft_readings' in selection:
                    features = deepcopy(selection['draft_readings'])
                member['biometrics'] = features
                member['sensor_quality'] = {key: 'missing' if value is None else 'invalid' if value < 0 else 'available' for key, value in features.items()}
        self._stage('analysis')
        # Set an explicit observation clock after generating the raw feature windows.
        clock = datetime.now(timezone.utc)
        end = clock.isoformat()
        voice_by_crew, wearable_by_crew = {}, {}
        for index, member in enumerate(samples[-1]['crew']):
            crew_id = member['crew_id']
            event = {'crew_id': crew_id, 'window_start': (clock - timedelta(seconds=60)).isoformat(),
                     'timestamp': end, 'data_origin': 'synthetic',
                     'feature_pipeline': 'wrist-bvp-eda-acc-60s-v1',
                     'biometrics': deepcopy(member['biometrics'])}
            raw_wearable = assess(event, model=self.model, now=end)
            wearable_by_crew[crew_id] = adapt_wearable(raw_wearable, crew_id=crew_id, now=end)
            profile = synth.SPEAKERS.get(crew_id)
            selection = selections.get(crew_id)
            aroused = (case == 'co2_rise' and index < 2) if checkins is None else bool(selection and selection['voice']=='aroused')
            audio = synth.utterance(synth.aroused(profile) if aroused else profile, 3, seed=5000 + index) if profile else np.zeros(48000)
            if (case == 'missing_sensor' and index == 0) or (selection and selection['voice']=='silence'):
                audio = np.zeros(48000)
            start = clock - timedelta(seconds=5)
            voice_result = self.voice.analyze(audio, crew_id, start.isoformat(), sr=16000, data_type='synthetic')
            if selection and selection['voice'].startswith(('artemis-','ravdess-')):
                from backend.test_lab import run_test
                nasa = run_test(self, {'kind':'voice', 'sample':selection['voice']})
                voice_result.record = None
                voice_result.details = {'method':'NASA_features_only' if selection['voice'].startswith('artemis-') else 'RAVDESS_features_only','crew_id':crew_id,
                                        'status':'baseline_unavailable', 'nasa_demo':nasa,
                                        'reason':'Recorded demonstration speaker is not this simulated crew member; no paired crew stress score.'}
            voice_by_crew[crew_id] = adapt_voice(
                voice_result.record, voice_result.details, crew_id=crew_id,
                window_end=(start + timedelta(seconds=len(audio) / 16000)).isoformat(),
                input_origin='synthetic', model_version=voice_result.details.get('method', 'personal_baseline_v1'), now=end)
        report = analyze_multimodal(samples[-1], self.profiles, previous=samples[0],
                                   snapshot_timestamp=end, now=end,
                                   voice_by_crew=voice_by_crew, wearable_by_crew=wearable_by_crew)
        self._stage('save')
        ids = []
        for index, sample in enumerate(samples):
            timestamp = (clock - timedelta(minutes=len(samples) - index - 1)).isoformat()
            ids.append(self.service.store.save_synthetic(timestamp, sample))
        identifier = self.service.log.save_analysis(ids[-1], report, previous_snapshot_id=ids[0])
        self.last_case = case
        self.checkins = selections
        self.progress = {**self.progress, 'status':'complete',
                         'steps':{key:'complete' for key in self.progress['steps']},
                         'elapsed_ms':round((time.monotonic()-self._started)*1000)}
        return identifier

    def bundle(self):
        result = export_bundle(self.service, limit=100)
        # Current UI reviews stay tied to this run. Full history remains in SQLite.
        snapshot_id = result['overview']['snapshot']['id'] if result['overview']['snapshot'] else None
        result['mission_logs'] = [entry for entry in result['mission_logs'] if entry['snapshot_id'] == snapshot_id]
        result['member_entries'] = {f'AST-{i:02}':self.entries.history(f'AST-{i:02}') for i in range(1,6)}
        result['demo_server'] = {
            'connected': True, 'scenario': self.last_case or result['overview']['snapshot']['payload'].get('scenario'), 'crew_count': 5,
            'signals': 'synthetic_audio_and_wrist_waveforms',
            'voice_method': 'personal_baseline_v1', 'wearable_model': self.model['version'],
            'crew_checkins': deepcopy(self.checkins),
            'supported_model_crew': list(synth.SPEAKERS),
        }
        return result
