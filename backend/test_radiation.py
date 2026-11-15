import unittest

from backend.radiation import RadiationConfig, radiation_reading
from backend.simulator import generate_scenario


class RadiationTests(unittest.TestCase):
    def test_units_and_piecewise_integration(self):
        self.assertEqual(radiation_reading(0)['dose_equivalent_since_run_start_msv'],0)
        self.assertEqual(radiation_reading(86400)['dose_equivalent_since_run_start_msv'],1.8)
        elevated = radiation_reading(86400,elevation_start_seconds=43200)
        self.assertAlmostEqual(elevated['dose_equivalent_since_run_start_msv'],4.5)
        self.assertEqual(elevated['dose_equivalent_rate_msv_per_day'],7.2)
        self.assertIsNone(elevated['career_dose_msv'])

    def test_simulated_crew_and_missing_sensor(self):
        for count in (4,5):
            samples = generate_scenario('radiation_rise',crew_count=count)
            doses = [s['crew'][0]['radiation']['dose_equivalent_since_run_start_msv'] for s in samples]
            self.assertEqual(doses,sorted(doses))
            self.assertEqual(len(samples[-1]['crew']),count)
            self.assertEqual(samples[-1]['crew'][0]['radiation']['dose_equivalent_rate_msv_per_day'],7.2)
        missing = generate_scenario('missing_sensor')[-1]['crew'][0]['radiation']
        self.assertEqual(missing['quality'],'missing')
        self.assertIsNone(missing['dose_equivalent_since_run_start_msv'])

    def test_invalid_inputs(self):
        for value in (-1,float('nan'),True):
            with self.assertRaises(ValueError):
                radiation_reading(value)
        for kwargs in ({'baseline_rate_msv_per_day':-1},{'elevated_multiplier':0.5}):
            with self.assertRaises(ValueError):
                RadiationConfig(**kwargs)
