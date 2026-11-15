"""Actual voice + wearable code on synthetic waveforms; offline integration demo.

Requires both owners' modules to be present in the environment. This branch does
not copy, merge, or modify their code. Replay clock and all raw signals are demo
inputs, not synchronized astronaut/research recordings.
"""
import argparse
import json
from datetime import timedelta
from pathlib import Path

from backend.crew import demo_profiles
from backend.multimodal import analyze_multimodal
from backend.service import MissionService
from backend.simulator import generate_scenario
from integration.adapters import utc, adapt_voice, adapt_wearable

CLOCK = '2026-11-15T12:00:00Z'


def run_demo(database, *, model_path, crew_count=5):
    import numpy as np
    from models.voice import VoiceStressEstimator
    from models.voice import synth
    from models.wearable import assess, load_model
    from models.wearable.signals import extract_window

    database = Path(database)
    if database.exists():
        raise ValueError('Use a new database path for this isolated integration demo')
    model = load_model(model_path)
    estimator = VoiceStressEstimator(baseline_path=None, model_path=None, auto_enroll=False)
    for index, (crew_id, profile) in enumerate(synth.SPEAKERS.items()):
        estimator.enroll(crew_id, [synth.utterance(profile, 3, seed=index * 100 + n)
                                 for n in range(10)], data_type='synthetic')
    samples = generate_scenario('co2_rise', crew_count=crew_count)
    current = samples[-1]
    voice_signals, wearable_signals = {}, {}
    clock = utc(CLOCK)
    for index, member in enumerate(current['crew']):
        crew_id = member['crew_id']
        # Real wearable extraction on explicitly synthetic 60-second wrist arrays.
        pulse_hz = 2 if index in (1, 2) else 1
        bvp = np.sin(2 * np.pi * pulse_hz * np.arange(3840) / 64)
        eda = np.full(240, 2.0)
        acc = np.tile([0, 0, 64], (1920, 1))
        features = extract_window(bvp, eda, acc)
        if index == 3:
            features['eda_microsiemens'] = None  # Deliberate summary dropout.
        event = {'crew_id': crew_id, 'timestamp': CLOCK,
                 'window_start': (clock - timedelta(seconds=60)).isoformat(),
                 'data_origin': 'synthetic',
                 'feature_pipeline': 'wrist-bvp-eda-acc-60s-v1', 'biometrics': features}
        wearable_raw = assess(event, model=model, now=CLOCK)
        wearable_signals[crew_id] = adapt_wearable(wearable_raw, crew_id=crew_id, now=CLOCK)
        member['biometrics'] = dict(features)
        profile = synth.SPEAKERS.get(crew_id)
        audio = (synth.utterance(synth.aroused(profile) if index == 1 else profile,
                                3, seed=5000 + index) if profile is not None else np.zeros(48000))
        if index == 3:
            audio = np.zeros(48000)  # Silence is missing voice, never score zero.
        start = clock - timedelta(seconds=5)
        result = estimator.analyze(audio, crew_id, start.isoformat(), sr=16000, data_type='synthetic')
        voice_signals[crew_id] = adapt_voice(
            result.record, result.details, crew_id=crew_id,
            window_end=(start + timedelta(seconds=len(audio) / 16000)).isoformat(),
            input_origin='synthetic', model_version=result.details.get('method', 'personal_baseline_v1'),
            now=CLOCK)
    report = analyze_multimodal(current, demo_profiles(crew_count), previous=samples[0],
                                snapshot_timestamp=CLOCK, now=CLOCK,
                                voice_by_crew=voice_signals, wearable_by_crew=wearable_signals)
    service = MissionService(database, clock=lambda: clock)
    service.initialize()
    service.store.register_synthetic_profiles(demo_profiles(crew_count))
    first = service.store.save_synthetic((clock - timedelta(seconds=660)).isoformat(), samples[0])
    last = service.store.save_synthetic(CLOCK, current)
    identifier = service.log.save_analysis(last, report, previous_snapshot_id=first)
    service.record_review(identifier, reviewer='Synthetic integration demo', decision='follow_up',
                          note='Software demonstration only; real crew review has not occurred.')
    view = service.overview()
    assert view['current_analysis']['report'] == report
    return {'data_origin': 'synthetic', 'clock': CLOCK, 'database': str(database),
            'analysis_id': identifier, 'report': report,
            'limitations': ['Actual model code executed on generated audio and wrist arrays.',
                            'No real astronaut data, model accuracy, or causal inference established.',
                            'Model input gaps remain unavailable; no normal score is fabricated.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--model-path', type=Path, required=True)
    parser.add_argument('--crew-count', type=int, choices=(4, 5), default=5)
    args = parser.parse_args()
    try:
        output = run_demo(args.database, model_path=args.model_path, crew_count=args.crew_count)
    except ImportError as error:
        parser.error('Both model owners\' modules and their dependencies must be available: ' + str(error))
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
