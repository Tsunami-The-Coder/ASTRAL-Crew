"""Internal composition of backend rules with separately adapted model outputs."""

from backend.cross_analysis import analyze_snapshot, RuleConfig
from fusion.rules import compare_modalities, FusionConfig
from fusion.adapters import utc, number
from copy import deepcopy


def analyze_multimodal(snapshot, profiles, *, snapshot_timestamp, now,
                       voice_by_crew=None, wearable_by_crew=None,
                       previous=None, rule_config=RuleConfig(), fusion_config=FusionConfig(),
                       max_age_seconds=300, max_snapshot_skew_seconds=60):
    """Existing telemetry report extended without modifying producer outputs.

    Model adapters must be invoked with the same explicit analysis clock first.
    Input keys must refer only to crew in this snapshot. No synthetic motion or
    feature_pipeline values are invented to force a wearable prediction.
    """
    observed, clock = utc(snapshot_timestamp), utc(now)
    if not number(max_age_seconds) or max_age_seconds <= 0 or not number(max_snapshot_skew_seconds) or max_snapshot_skew_seconds < 0:
        raise ValueError('Invalid demo freshness/alignment settings')
    if observed > clock or (clock - observed).total_seconds() > max_age_seconds:
        raise ValueError('Telemetry snapshot is stale or future-dated at the analysis clock')
    report = analyze_snapshot(snapshot, profiles, previous=previous, config=rule_config)
    voice_by_crew = {} if voice_by_crew is None else voice_by_crew
    wearable_by_crew = {} if wearable_by_crew is None else wearable_by_crew
    if not isinstance(voice_by_crew, dict) or not isinstance(wearable_by_crew, dict):
        raise ValueError('Modality inputs must be maps keyed by crew ID')
    roster = {member['crew_id'] for member in snapshot['crew']}
    if (set(voice_by_crew) | set(wearable_by_crew)) - roster:
        raise ValueError('Modality input references crew absent from snapshot')
    def aligned(signal):
        if not isinstance(signal, dict) or signal.get('status') != 'available':
            return signal
        signal = deepcopy(signal)
        try:
            if signal.get('input_origin') != snapshot.get('data_origin'):
                raise ValueError('Model input provenance differs from telemetry')
            if abs((utc(signal['window_end']) - observed).total_seconds()) > max_snapshot_skew_seconds:
                raise ValueError('Model window is not aligned with telemetry snapshot')
        except (KeyError, ValueError, TypeError) as error:
            signal.update(status='not_aligned', stress_score=None)
            signal.setdefault('issues', []).append(str(error))
        return signal
    results = [compare_modalities(crew_id, now=now, voice=aligned(voice_by_crew.get(crew_id)),
                                 wearable=aligned(wearable_by_crew.get(crew_id)), config=fusion_config,
                                 max_age_seconds=max_age_seconds)
               for crew_id in sorted(roster)]
    report['base_rules_version'] = report['rules_version']
    report['rules_version'] = 'internal-multimodal-v1'
    report['multimodal'] = results
    report['model_alignment'] = {'snapshot_timestamp': snapshot_timestamp, 'analysis_clock': now,
                                 'max_age_seconds': max_age_seconds,
                                 'max_snapshot_skew_seconds': max_snapshot_skew_seconds}
    for result in results:
        report['findings'].extend(result['findings'])
    report['needs_review'] = bool(report['needs_review'] or any(r['needs_review'] for r in results))
    report['limitations'] = [line for line in report['limitations'] if 'not consumed yet' not in line]
    report['limitations'].append('Internal model adapter proposal; shared interface and calibration approval pending.')
    # The base report describes raw observations only, not availability of new outputs.
    for crew in report['crew']:
        result = next(item for item in results if item['crew_id'] == crew['crew_id'])
        crew['unavailable_models'] = [source for source, signal in result['signals'].items()
                                      if not isinstance(signal, dict) or signal.get('status') != 'available'
                                      or signal.get('crew_id') != crew['crew_id'] or signal.get('source') != source]
    return report
