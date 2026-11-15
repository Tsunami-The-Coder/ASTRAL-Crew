"""Qualitative comparison of normalized evidence; no numeric score fusion."""

from dataclasses import asdict, dataclass
from integration.adapters import number, utc


@dataclass(frozen=True)
class FusionConfig:
    voice_low_score: float = 0.4
    voice_elevated_score: float = 0.6
    wearable_low_score: float = 0.4
    wearable_elevated_score: float = 0.6
    minimum_voice_confidence: float = 0.5

    def __post_init__(self):
        if (not all(number(v) for v in asdict(self).values())
                or not 0 <= self.voice_low_score < self.voice_elevated_score <= 1
                or not 0 <= self.wearable_low_score < self.wearable_elevated_score <= 1
                or not 0 <= self.minimum_voice_confidence <= 1):
            raise ValueError('Invalid demo comparison settings')


def compare_modalities(crew_id, *, now, voice=None, wearable=None, config=FusionConfig(),
                       max_age_seconds=300):
    """Demo bands are uncalibrated engineering settings, not clinical states.

    Freshness is checked again against the explicit analysis clock, even if
    adapters were called earlier. This is snapshot/window freshness, not raw-sensor QA.
    """
    clock = utc(now)
    if not number(max_age_seconds) or max_age_seconds <= 0:
        raise ValueError('max_age_seconds must be finite and positive')
    signals = {'voice': voice, 'wearable': wearable}
    issues, findings, usable = [], [], {}
    for source, signal in signals.items():
        if signal is None:
            issues.append(source + ': missing')
            continue
        if not isinstance(signal, dict) or signal.get('source') != source or signal.get('crew_id') != crew_id:
            issues.append(source + ': identity/source mismatch')
            continue
        if signal.get('status') != 'available':
            issues.append(source + ': ' + str(signal.get('status')))
            continue
        if not number(signal.get('stress_score')) or not 0 <= signal['stress_score'] <= 1:
            issues.append(source + ': invalid score')
            continue
        if source == 'voice' and (not number(signal.get('confidence')) or signal['confidence'] < config.minimum_voice_confidence):
            issues.append('voice: confidence below demo comparison setting')
            continue
        if not isinstance(signal.get('quality'), dict):
            issues.append(source + ': malformed quality')
            continue
        if source == 'wearable' and signal['quality'].get('status') == 'motion_caution':
            findings.append({'code': 'MOVEMENT_CAUTION', 'crew_id': crew_id,
                             'message': 'Movement may confound wearable interpretation; review context.'})
            issues.append('wearable: movement caution; paired interpretation withheld')
            continue
        try:
            start, end = utc(signal['window_start']), utc(signal['window_end'])
            if start >= end or end > clock or (clock - end).total_seconds() > max_age_seconds:
                issues.append(source + ': stale/future/invalid observation window')
                continue
        except (KeyError, ValueError, TypeError):
            issues.append(source + ': malformed observation window')
            continue
        usable[source] = signal
    status = 'unavailable' if not usable else 'partial'
    agreement = None
    if len(usable) == 2:
        v, w = usable['voice'], usable['wearable']
        try:
            start = max(utc(v['window_start']), utc(w['window_start']))
            end = min(utc(v['window_end']), utc(w['window_end']))
            if start >= end:
                issues.append('Observation windows do not overlap')
            elif v.get('input_origin') != w.get('input_origin'):
                issues.append('Input origins differ; real synchronization is unestablished')
            else:
                status = 'compared'
                vs, ws = v['stress_score'], w['stress_score']
                if vs >= config.voice_elevated_score and ws >= config.wearable_elevated_score:
                    agreement = 'both_elevated'
                    findings.append({'code': 'BOTH_INDICATORS_ELEVATED', 'crew_id': crew_id,
                                     'message': 'Both demo indicator bands are elevated; human review recommended. Cause unresolved.'})
                elif ((vs >= config.voice_elevated_score and ws <= config.wearable_low_score)
                      or (ws >= config.wearable_elevated_score and vs <= config.voice_low_score)):
                    agreement = 'disagreement'
                    findings.append({'code': 'MODALITY_DISAGREEMENT', 'crew_id': crew_id,
                                     'message': 'Voice and wearable indicators differ. Verify signals and crew context; a calm voice does not rule out a physiological problem.'})
                elif vs <= config.voice_low_score and ws <= config.wearable_low_score:
                    agreement = 'both_below_demo_band'
                else:
                    agreement = 'inconclusive'
        except (KeyError, ValueError, TypeError):
            issues.append('Malformed observation windows')
    return {'crew_id': crew_id, 'status': status, 'agreement': agreement,
            'combined_score': None, 'signals': signals, 'issues': issues,
            'findings': findings, 'needs_review': bool(findings),
            'config': asdict(config),
            'limitations': ['Scores have different meanings and are not averaged.',
                            'Demo bands are unvalidated; no diagnosis, safety clearance, or autonomous action.',
                            'Synthetic alignment is scripted, not synchronized research evidence.']}
