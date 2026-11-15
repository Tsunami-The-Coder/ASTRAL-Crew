"""Internal adapters for existing owner handoffs; shared contract unchanged."""

from copy import deepcopy
from datetime import datetime, timezone
from math import isfinite
import json

ORIGINS = {'synthetic', 'research', 'replayed', 'measured'}


def utc(value):
    if not isinstance(value, str):
        raise ValueError('Explicit timezone-aware ISO timestamp required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Timestamp requires a timezone')
    return parsed.astimezone(timezone.utc)


def number(value):
    return type(value) in (int, float) and isfinite(value)


def _base(source, crew_id, raw):
    capture_issues = []
    try:
        json.dumps(raw, allow_nan=False)
        captured = deepcopy(raw)
    except (ValueError, TypeError):
        captured = None
        capture_issues = ['Non-JSON producer payload rejected; raw capture omitted, not normalized to normal values']
    return {'source': source, 'crew_id': crew_id, 'status': 'invalid' if capture_issues else 'missing',
            'stress_score': None, 'confidence': None, 'window_start': None,
            'window_end': None, 'input_origin': None, 'inference_origin': None,
            'model_version': None, 'score_semantics': None, 'quality': {},
            'limitations': [], 'issues': capture_issues, 'raw': captured}


def _window(result, start, end, now, max_age_seconds):
    if not number(max_age_seconds) or max_age_seconds <= 0:
        raise ValueError('max_age_seconds must be finite and positive')
    start, end, clock = utc(start), utc(end), utc(now)
    if start >= end or end > clock:
        raise ValueError('Observation window must have positive duration and not be future-dated')
    result.update(window_start=start.isoformat(), window_end=end.isoformat())
    if (clock - end).total_seconds() > max_age_seconds:
        result['status'] = 'stale'
        result['issues'].append('Observation window is stale')
        return False
    return True


def adapt_voice(record, details, *, crew_id, window_end, input_origin,
                model_version, now, max_age_seconds=300):
    """Caller supplies actual audio end and method/artifact version, never guesses.

    Voice data_type=real is ambiguous: caller must explicitly distinguish measured,
    research and replayed input. Raw data_type is retained, not silently renamed.
    """
    result = _base('voice', crew_id, {'record': record, 'details': details})
    if result['issues']:
        return result
    if not isinstance(details, dict):
        result.update(status='invalid', issues=['Voice details must be an object'])
        return result
    if record is None:
        source_status = details.get('status')
        result['status'] = {'no_speech': 'missing', 'enrolling_baseline': 'baseline_pending',
                            'invalid_input': 'invalid'}.get(source_status, 'missing')
        result['issues'].append('No voice record: ' + str(source_status))
        return result
    try:
        if not isinstance(record, dict) or record.get('source') != 'voice':
            raise ValueError('Expected a voice record')
        if record.get('crew_id') != crew_id or details.get('crew_id') != crew_id:
            raise ValueError('Voice crew identity mismatch')
        if details.get('status') != 'ok':
            raise ValueError('Voice record is not usable')
        if not isinstance(model_version, str) or not model_version.strip():
            raise ValueError('Explicit voice method/artifact version required')
        if input_origin not in ORIGINS:
            raise ValueError('Explicit input_origin required')
        if ((record.get('data_type') == 'synthetic' and input_origin != 'synthetic')
                or (record.get('data_type') == 'real' and input_origin == 'synthetic')
                or record.get('data_type') not in ('real', 'synthetic')):
            raise ValueError('Voice provenance mismatch')
        score, confidence = record.get('stress_score'), record.get('confidence')
        if not number(score) or not 0 <= score <= 1 or not number(confidence) or not 0 <= confidence <= 1:
            raise ValueError('Invalid voice score/confidence')
        result.update(input_origin=input_origin, model_version=model_version,
                      inference_origin='personal_baseline_indicator',
                      score_semantics='personal_baseline_vocal_arousal',
                      quality=deepcopy(details.get('quality', {})),
                      limitations=['Vocal arousal is not specific to stress; confidence is heuristic.'])
        if _window(result, record.get('timestamp'), window_end, now, max_age_seconds):
            result.update(status='available', stress_score=score, confidence=confidence)
    except (ValueError, TypeError) as error:
        result.update(status='invalid', stress_score=None)
        result['issues'].append(str(error))
    return result


def adapt_wearable(raw, *, crew_id, now, max_age_seconds=300):
    result = _base('wearable', crew_id, raw)
    if raw is None or result['issues']:
        return result
    try:
        if not isinstance(raw, dict) or raw.get('source') != 'wearable' or raw.get('schema_version') != 'wearable-proposal-v1':
            raise ValueError('Expected wearable-proposal-v1 output')
        if raw.get('crew_id') != crew_id:
            raise ValueError('Wearable crew identity mismatch')
        status = raw.get('status')
        if status not in {'available', 'missing', 'invalid', 'stale', 'model_unavailable', 'model_invalid', 'incompatible_features'}:
            raise ValueError('Unknown wearable status')
        result.update(status=status, input_origin=raw.get('data_origin'),
                      inference_origin=raw.get('inference_origin'),
                      score_semantics=raw.get('score_semantics'), model_version=raw.get('model_version'),
                      quality=deepcopy(raw.get('quality', {})), limitations=deepcopy(raw.get('limitations', [])))
        if status != 'available':
            if raw.get('stress_score') is not None:
                raise ValueError('Unavailable wearable result must have null score')
            return result
        if raw.get('data_origin') not in ORIGINS:
            raise ValueError('Missing wearable input provenance')
        score = raw.get('stress_score')
        if not number(score) or not 0 <= score <= 1:
            raise ValueError('Invalid wearable score')
        if not isinstance(raw.get('model_version'), str) or not raw['model_version']:
            raise ValueError('Wearable model_version required')
        if raw.get('score_semantics') not in ('synthetic_demo_score','uncalibrated_WESAD_stress_class_probability'):
            raise ValueError('Unknown wearable score semantics')
        if raw.get('confidence') is not None:
            raise ValueError('Wearable confidence must remain null under its current handoff')
        if _window(result, raw.get('window_start'), raw.get('timestamp'), now, max_age_seconds):
            result.update(status='available', stress_score=score)
        else:
            result['stress_score'] = None
    except (ValueError, TypeError) as error:
        result.update(status='invalid', stress_score=None)
        result['issues'].append(str(error))
    return result
