"""Adapter/fusion engineering fixtures, not trained-model validation."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.crew import demo_profiles
from backend.multimodal import analyze_multimodal
from backend.service import MissionService
from backend.simulator import generate_scenario
from fusion.adapters import adapt_voice, adapt_wearable
from fusion.rules import compare_modalities, FusionConfig

NOW = '2026-11-15T12:00:00Z'


def voice(score=0.8, **changes):
    record = dict(crew_id='AST-01', timestamp='2026-11-15T11:59:55Z', source='voice',
                  data_type='synthetic', stress_score=score, confidence=0.8)
    record.update(changes)
    return adapt_voice(record, dict(status='ok', crew_id='AST-01', quality={}),
                       crew_id='AST-01', window_end='2026-11-15T11:59:58Z',
                       input_origin='synthetic', model_version='test-fixture-voice', now=NOW)


def wearable(score=0.8, **changes):
    result = dict(schema_version='wearable-proposal-v1', source='wearable',crew_id='AST-01',
                  status='available', stress_score=score, confidence=None,
                  timestamp='2026-11-15T12:00:00Z',window_start='2026-11-15T11:59:00Z',
                  data_origin='synthetic', inference_origin='simulated_inference',
                  score_semantics='synthetic_demo_score',model_version='test-fixture-wearable',
                  quality={'status':'usable_summary'},limitations=['Synthetic test fixture'])
    result.update(changes)
    return adapt_wearable(result,crew_id='AST-01',now=NOW)


class MultimodalTests(unittest.TestCase):
    def test_elevation_and_disagreement_without_averaging(self):
        result = compare_modalities('AST-01',now=NOW,voice=voice(),wearable=wearable())
        self.assertEqual(result['agreement'],'both_elevated')
        self.assertIsNone(result['combined_score'])
        result = compare_modalities('AST-01',now=NOW,voice=voice(0.1),wearable=wearable())
        self.assertEqual(result['findings'][0]['code'],'MODALITY_DISAGREEMENT')
        self.assertNotIn('fault',result['findings'][0]['message'].lower())

    def test_absence_enrollment_and_invalid_inputs_remain_explicit(self):
        for status,expected in [('no_speech','missing'),('enrolling_baseline','baseline_pending'),('invalid_input','invalid')]:
            result=adapt_voice(None,{'status':status},crew_id='AST-01',window_end=None,
                               input_origin='synthetic',model_version='fixture',now=NOW)
            self.assertEqual(result['status'],expected)
            self.assertIsNone(result['stress_score'])
        self.assertEqual(compare_modalities('AST-01',now=NOW)['status'],'unavailable')
        self.assertEqual(compare_modalities('AST-01',now=NOW,wearable=wearable())['status'],'partial')
        self.assertEqual(voice(float('nan'))['status'],'invalid')
        self.assertEqual(wearable(1.1)['status'],'invalid')

    def test_stale_future_and_malformed_windows(self):
        self.assertEqual(wearable(timestamp='2026-11-15T11:50:00Z',window_start='2026-11-15T11:49:00Z')['status'],'stale')
        self.assertEqual(wearable(timestamp='2026-11-15T12:01:00Z')['status'],'invalid')
        self.assertEqual(wearable(window_start='2026-11-15T12:00:00Z')['status'],'invalid')
        self.assertEqual(wearable(window_start='not a date')['status'],'invalid')

    def test_identity_nonoverlap_and_origin_mismatch_not_compared(self):
        self.assertEqual(voice(crew_id='AST-02')['status'],'invalid')
        result=compare_modalities('AST-02',now=NOW,voice=voice(),wearable=wearable())
        self.assertEqual(result['status'],'unavailable')
        result=compare_modalities('AST-01',now=NOW,voice=voice(),wearable=wearable(
            window_start='2026-11-15T11:58:00Z',timestamp='2026-11-15T11:59:00Z'))
        self.assertNotEqual(result['status'],'compared')
        result=compare_modalities('AST-01',now=NOW,voice=voice(),wearable=wearable(data_origin='research'))
        self.assertNotEqual(result['status'],'compared')

    def test_quality_limits_and_null_wearable_confidence_preserved(self):
        self.assertIsNone(wearable()['confidence'])
        low=compare_modalities('AST-01',now=NOW,voice=voice(confidence=0.1),wearable=wearable())
        self.assertEqual(low['status'],'partial')
        motion=compare_modalities('AST-01',now=NOW,voice=voice(),wearable=wearable(quality={'status':'motion_caution'}))
        self.assertEqual(motion['findings'][0]['code'],'MOVEMENT_CAUTION')
        self.assertNotEqual(motion['status'],'compared')

    def test_unavailable_wearable_cannot_carry_normal_score(self):
        self.assertEqual(wearable(status='missing')['status'],'invalid')
        item=wearable(score=None,status='model_unavailable')
        self.assertEqual(item['status'],'model_unavailable')
        self.assertIsNone(item['stress_score'])

    def test_five_crew_report_logs_and_service_with_missing_fifth(self):
        samples=generate_scenario('co2_rise')
        original=copy.deepcopy(samples)
        report=analyze_multimodal(samples[-1],demo_profiles(),previous=samples[0],snapshot_timestamp=NOW,now=NOW,
                                 voice_by_crew={'AST-01':voice()},wearable_by_crew={'AST-01':wearable()})
        self.assertEqual(samples,original)
        self.assertEqual(report['multimodal'][-1]['crew_id'],'AST-05')
        self.assertEqual(report['multimodal'][-1]['status'],'unavailable')
        self.assertIn('POSSIBLE_ENVIRONMENTAL_ASSOCIATION',[f['code'] for f in report['findings']])
        self.assertIn('BOTH_INDICATORS_ELEVATED',[f['code'] for f in report['findings']])
        json.dumps(report,allow_nan=False)
        with tempfile.TemporaryDirectory() as folder:
            service=MissionService(Path(folder)/'mission.sqlite3',clock=lambda:datetime.fromisoformat(NOW.replace('Z','+00:00')))
            service.initialize()
            first=service.store.save_synthetic('2026-11-15T11:49:00Z',samples[0])
            last=service.store.save_synthetic(NOW,samples[-1])
            service.log.save_analysis(last,report,previous_snapshot_id=first)
            self.assertEqual(service.overview()['current_analysis']['report'],report)

    def test_unknown_crew_and_invalid_config(self):
        with self.assertRaises(ValueError):
            analyze_multimodal(generate_scenario()[-1],demo_profiles(),snapshot_timestamp=NOW,now=NOW,voice_by_crew={'AST-99':voice()})
        with self.assertRaises(ValueError):
            FusionConfig(voice_low_score=0.9,voice_elevated_score=0.6)

    def test_ambiguous_voice_origin_requires_explicit_consistent_choice(self):
        result=voice(data_type='real')
        self.assertEqual(result['status'],'invalid')
        self.assertEqual(result['raw']['record']['data_type'],'real')

    def test_adapter_does_not_mutate_producer_result(self):
        result=wearable()
        before=copy.deepcopy(result['raw'])
        compare_modalities('AST-01',now=NOW,voice=voice(),wearable=result)
        self.assertEqual(result['raw'],before)


    def test_cached_evidence_is_not_fresh_forever(self):
        report=compare_modalities('AST-01',now='2026-11-15T12:10:00Z',
                                  voice=voice(),wearable=wearable())
        self.assertEqual(report['status'],'unavailable')
        self.assertEqual(report['findings'],[])

    def test_model_to_snapshot_skew_and_provenance_are_checked(self):
        samples=generate_scenario()
        report=analyze_multimodal(samples[-1],demo_profiles(),
            snapshot_timestamp='2026-11-15T11:57:00Z',now=NOW,
            voice_by_crew={'AST-01':voice()},wearable_by_crew={'AST-01':wearable()})
        self.assertEqual(report['multimodal'][0]['status'],'unavailable')
        with self.assertRaises(ValueError):
            analyze_multimodal(samples[-1],demo_profiles(),
                snapshot_timestamp='2026-11-15T11:00:00Z',now=NOW)

    def test_invalid_raw_payload_is_json_safe_and_explicit(self):
        invalid=voice(float('nan'))
        self.assertEqual(invalid['status'],'invalid')
        self.assertIsNone(invalid['raw'])
        self.assertTrue(invalid['issues'])
        json.dumps(invalid,allow_nan=False)
