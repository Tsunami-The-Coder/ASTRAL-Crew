"""Local sample tests; uploaded audio is decoded in memory and never persisted."""
import base64
from pathlib import Path
from io import BytesIO
from datetime import datetime, timezone
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
from math import gcd
from models.voice import VoiceStressEstimator, synth
from models.wearable import assess
from models.wearable.signals import extract_window

VOICE_SAMPLES = {'calm': False, 'aroused': True, 'silence': None}

def sample_wav(name, crew_id="AST-01"):
    if name not in VOICE_SAMPLES:
        raise ValueError('Unknown voice sample')
    if crew_id not in synth.SPEAKERS:
        raise ValueError('Voice sample unavailable for this crew ID')
    profile = synth.SPEAKERS[crew_id]
    audio = np.zeros(48000) if name == 'silence' else synth.utterance(synth.aroused(profile) if name == 'aroused' else profile, 3, seed=5000 + list(synth.SPEAKERS).index(crew_id))
    output = BytesIO()
    wavfile.write(output, 16000, (np.clip(audio, -1, 1) * 32767).astype(np.int16))
    return output.getvalue()

def decode_wav(encoded):
    if not isinstance(encoded, str):
        raise ValueError('WAV content required')
    try:
        raw = base64.b64decode(encoded, validate=True)
        rate, audio = wavfile.read(BytesIO(raw))
    except Exception as error:
        raise ValueError('Unreadable WAV file') from error
    if not 8000 <= rate <= 96000 or audio.ndim not in (1, 2) or not 1 <= len(audio) / rate <= 20:
        raise ValueError('Use a 1–20 second WAV at 8–96 kHz')
    if audio.dtype.kind == 'u':
        audio = (audio.astype(float) - 128) / 128
    elif audio.dtype.kind == 'i':
        audio = audio.astype(float) / max(abs(np.iinfo(audio.dtype).min), np.iinfo(audio.dtype).max)
    elif audio.dtype.kind != 'f':
        raise ValueError('Unsupported WAV encoding')
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if not np.isfinite(audio).all():
        raise ValueError('Non-finite audio')
    divisor = gcd(int(rate), 16000)
    return resample_poly(audio, 16000 // divisor, int(rate) // divisor)

def run_test(engine, data):
    kind, sample = data.get('kind'), data.get('sample')
    now = datetime.now(timezone.utc).isoformat()
    if kind == 'voice' and sample in ('ravdess-calm', 'ravdess-neutral', 'ravdess-fearful'):
        from models.voice.features import load_wav, extract
        import json
        folder=Path(__file__).resolve().parents[1]/'submission/astral-prototype/audio/ravdess'
        manifest=json.loads((folder/'manifest.json').read_text())
        label=sample.split('-')[1]
        metadata=next(item for item in manifest['files'] if item['label']==label)
        features=extract(load_wav(folder/metadata['file']),16000)
        return {'kind':'voice','origin':'RAVDESS acted '+label+' recording',
                'result':{'stress_score':None,'status':'features_extracted','quality':features.quality.as_dict(),
                          'features':features.values,'reason':'Acted emotion label is not a physiological stress label or a simulated crew baseline.'},
                'source':{**metadata,'title':'RAVDESS · '+label,'credit':manifest['authors'],'source_page':manifest['source'],'license':manifest['license']},
                'steps':['Original labelled WAV decoded','Speech quality checked','Voice features extracted','Acted label retained; no crew stress score invented'],
                'scope':'Recorded sample demonstration. Speaker is Actor 01, not a mission crew member.'}
    if kind == 'voice' and sample in ('artemis-terminator', 'artemis-closest'):
        from models.voice.features import load_wav, extract
        import json
        folder = Path(__file__).resolve().parents[1] / 'submission/astral-prototype/audio'
        metadata = next(item for item in json.loads((folder/'manifest.json').read_text()) if item['id'] == sample)
        features = extract(load_wav(folder/(sample+'.wav')), 16000)
        return {'kind': kind, 'origin': 'NASA Artemis II recorded audio excerpt',
                'result': {'stress_score': None, 'status': 'features_extracted',
                           'quality': features.quality.as_dict(), 'features': features.values,
                           'reason': 'No verified same-speaker calm baseline or stress labels; no stress score assigned.'},
                'source': metadata,
                'steps': ['NASA WAV excerpt decoded', 'Band-pass and speech quality checks run', 'Pitch / MFCC / Teager energy features extracted', 'Stress scoring withheld: no verified personal baseline'],
                'scope': 'Real recorded audio demonstration only. Not paired with wearable samples; not astronaut stress validation.'}
    if kind == 'voice':
        if sample == 'upload':
            calm = data.get('baseline_wavs')
            if not isinstance(calm, list) or not 5 <= len(calm) <= 10:
                raise ValueError('Provide 5–10 calm recordings from the same speaker as the test WAV')
            estimator = VoiceStressEstimator(baseline_path=None, model_path=None, auto_enroll=False, min_enroll=5)
            estimator.enroll('AST-01', [decode_wav(x) for x in calm], data_type='real')
            result = estimator.analyze(decode_wav(data.get('test_wav')), 'AST-01', now, data_type='real')
            origin = 'uploaded recording'
        else:
            if sample not in VOICE_SAMPLES:
                raise ValueError('Unknown voice sample')
            profile = synth.SPEAKERS['AST-01']
            audio = np.zeros(48000) if sample == 'silence' else synth.utterance(synth.aroused(profile) if sample == 'aroused' else profile, 3, seed=5000)
            result = engine.voice.analyze(audio, 'AST-01', now, data_type='synthetic')
            origin = 'synthetic speech-like signal'
        return {'kind': kind, 'origin': origin, 'result': {'record': result.record, 'details': result.details},
                'steps': ['WAV decoded', 'Speech quality checked', 'Voice features extracted', 'Compared with same-speaker calm baseline'],
                'scope': 'Standalone voice test. No paired wearable or cabin inference is made.'}
    if kind == 'wearable':
        if sample == 'upload':
            raw = data.get('signals')
            if not isinstance(raw, dict):
                raise ValueError('JSON must contain BVP, EDA and ACC arrays')
            features = extract_window(raw.get('BVP'), raw.get('EDA'), raw.get('ACC'))
            origin = 'replayed'
        else:
            if sample not in ('rest', 'elevated', 'movement', 'missing'):
                raise ValueError('Unknown wearable sample')
            features = engine._wrist_features(2.0 if sample in ('elevated','movement') else 1.0,
                                             moving=sample == 'movement', eda_level=2.8 if sample == 'elevated' else 2.0)
            if sample == 'missing':
                features['eda_microsiemens'] = None
            origin = 'synthetic'
        from datetime import timedelta
        event = {'crew_id': 'AST-01', 'timestamp': now,
                 'window_start': (datetime.fromisoformat(now)-timedelta(seconds=60)).isoformat(),
                 'data_origin': origin, 'feature_pipeline': 'wrist-bvp-eda-acc-60s-v1', 'biometrics': features}
        # Recorded inputs use an explicit replay clock; no claim of current measurements.
        result = assess(event, model=engine.model, now=now)
        return {'kind': kind, 'origin': origin, 'features': features, 'result': result,
                'steps': ['60-second window prepared', 'Pulse / EDA / motion features extracted', 'WESAD-trained model evaluated', 'Quality and motion rules checked'],
                'scope': 'Standalone wearable test. Samples are not paired with a voice recording.'}
    raise ValueError('Choose voice or wearable')
