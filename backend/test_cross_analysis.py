import copy
import unittest

from backend.crew import demo_profiles
from backend.simulator import generate_scenario
from backend.cross_analysis import analyze_snapshot, RuleConfig


class AnalysisTests(unittest.TestCase):
    def analyze(self, scenario, count=5):
        samples = generate_scenario(scenario, crew_count=count)
        return analyze_snapshot(samples[-1], demo_profiles(count), previous=samples[0])

    def test_baseline_has_no_findings_but_models_remain_unavailable(self):
        report = self.analyze('baseline')
        self.assertEqual(report['findings'], [])
        self.assertTrue(all(c['unavailable_models'] == ['voice', 'wearable_inference']
                            for c in report['crew']))

    def test_shared_change_and_possible_association_for_four_and_five(self):
        for count in (4, 5):
            report = self.analyze('co2_rise', count)
            self.assertEqual([f['code'] for f in report['findings']],
                             ['SHARED_CREW_CHANGE', 'POSSIBLE_ENVIRONMENTAL_ASSOCIATION'])
            self.assertEqual(len(report['findings'][0]['crew_ids']), count)
            self.assertTrue(report['needs_review'])

    def test_missing_and_invalid_remain_distinct(self):
        missing = self.analyze('missing_sensor')
        faulty = self.analyze('faulty_sensor')
        self.assertIn('missing', [i['status'] for i in missing['input_issues']])
        self.assertIn('invalid', [i['status'] for i in faulty['input_issues']])
        self.assertEqual(missing['findings'], [])
        self.assertEqual(faulty['findings'], [])

    def test_no_environmental_conclusion_without_comparison(self):
        current = generate_scenario('co2_rise')[-1]
        report = analyze_snapshot(current, demo_profiles())
        self.assertEqual([f['code'] for f in report['findings']], ['SHARED_CREW_CHANGE'])
        self.assertIsNone(report['co2_delta_percentage_points'])

    def test_missing_reference_and_corrupt_values_do_not_become_normal(self):
        current = generate_scenario()[-1]
        current['crew'][0]['biometrics']['heart_rate_bpm'] = float('nan')
        report = analyze_snapshot(current, [])
        self.assertTrue(report['needs_review'])
        self.assertEqual(report['findings'], [])
        self.assertIn('invalid', [i['status'] for i in report['input_issues']])

    def test_does_not_use_scenario_answer_or_modify_inputs(self):
        samples = generate_scenario('co2_rise')
        original = copy.deepcopy(samples)
        expected = analyze_snapshot(samples[-1], demo_profiles(), previous=samples[0])
        self.assertEqual(samples, original)
        samples[-1]['scenario'] = 'baseline'
        samples[-1]['cabin_model'] = {'fake_answer': 'all safe'}
        self.assertEqual(analyze_snapshot(samples[-1], demo_profiles(), previous=samples[0]), expected)

    def test_configurable_thresholds(self):
        samples = generate_scenario('co2_rise')
        report = analyze_snapshot(samples[-1], demo_profiles(), previous=samples[0],
                                  config=RuleConfig(minimum_changed_crew=6))
        self.assertEqual(report['findings'], [])
        with self.assertRaises(ValueError):
            RuleConfig(heart_rate_increase_bpm=-1)

    def test_malformed_structure_and_duplicate_crew(self):
        with self.assertRaises(ValueError):
            analyze_snapshot({}, demo_profiles())
        snapshot = generate_scenario()[-1]
        snapshot['crew'].append(copy.deepcopy(snapshot['crew'][0]))
        with self.assertRaises(ValueError):
            analyze_snapshot(snapshot, demo_profiles())
