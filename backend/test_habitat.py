import unittest

from backend.crew import demo_profiles
from backend.cross_analysis import analyze_snapshot,RuleConfig
from backend.simulator import generate_scenario


class HabitatTests(unittest.TestCase):
    def report(self,scenario):
        samples=generate_scenario(scenario)
        return analyze_snapshot(samples[-1],demo_profiles(),previous=samples[0])

    def test_pressure_drop_with_unchanged_fraction_lowers_partial_pressure(self):
        samples=generate_scenario('pressure_drop')
        report=self.report('pressure_drop')
        self.assertEqual([f['code'] for f in report['findings']],['CABIN_PRESSURE_DROP'])
        self.assertEqual(samples[-1]['environment']['o2_percent'],21)
        self.assertAlmostEqual(report['habitat']['o2_partial_pressure_kpa'],20.16)
        self.assertTrue(report['needs_review'])

    def test_oxygen_fraction_drop_independent_of_pressure(self):
        report=self.report('oxygen_drop')
        self.assertEqual([f['code'] for f in report['findings']],['CABIN_OXYGEN_FRACTION_DROP'])
        self.assertEqual(report['habitat']['pressure_delta_kpa'],0)
        self.assertEqual(report['habitat']['o2_delta_percentage_points'],-3)

    def test_missing_and_invalid_inputs_do_not_become_drop_findings(self):
        for scenario in ('missing_sensor','faulty_sensor'):
            report=self.report(scenario)
            self.assertEqual(report['findings'],[])
            self.assertIsNone(report['habitat']['o2_partial_pressure_kpa'])
            self.assertTrue(report['input_issues'])

    def test_no_prior_and_nonfinite_or_out_of_range_values(self):
        sample=generate_scenario('pressure_drop')[-1]
        self.assertEqual(analyze_snapshot(sample,demo_profiles())['findings'],[])
        for value in (101,float('nan'),True,-1):
            sample['environment']['o2_percent']=value
            report=analyze_snapshot(sample,demo_profiles())
            self.assertIsNone(report['habitat']['o2_partial_pressure_kpa'])
            self.assertIn('invalid',[issue['status'] for issue in report['input_issues']])

    def test_thresholds_and_fixture_metadata_do_not_define_answer(self):
        samples=generate_scenario('pressure_drop')
        samples[-1]['scenario']='baseline'
        report=analyze_snapshot(samples[-1],demo_profiles(),previous=samples[0])
        self.assertEqual(report['findings'][0]['code'],'CABIN_PRESSURE_DROP')
        report=analyze_snapshot(samples[-1],demo_profiles(),previous=samples[0],
                                config=RuleConfig(pressure_decrease_kpa=10))
        self.assertEqual(report['findings'],[])
