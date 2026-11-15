import unittest

from backend.cabin import CabinConfig, co2_percent_after
from backend.simulator import generate_scenario


class CabinTests(unittest.TestCase):
    def test_zero_time_and_balanced_removal(self):
        self.assertEqual(co2_percent_after(0, 5), 0.1)
        self.assertEqual(co2_percent_after(86400, 5, CabinConfig(removal_fraction=1)), 0.1)

    def test_hand_calculated_increment(self):
        # 100 m3, 101 kPa, 295.15 K: 5.2 kg/day = 0.003611 kg/min.
        # Ideal gas gives about 4115.63 mol cabin gas, 0.08205 mol CO2/min.
        self.assertAlmostEqual(co2_percent_after(60, 5) - 0.1, 0.0019934, places=6)

    def test_volume_crew_and_removal_scaling(self):
        increment = co2_percent_after(600, 5) - 0.1
        self.assertAlmostEqual(co2_percent_after(600, 10) - 0.1, increment * 2)
        self.assertAlmostEqual(co2_percent_after(600, 5, CabinConfig(volume_m3=200)) - 0.1,
                               increment / 2)
        self.assertAlmostEqual(co2_percent_after(600, 5, CabinConfig(removal_fraction=0.5)) - 0.1,
                               increment / 2)

    def test_invalid_parameters(self):
        for config in ({"volume_m3": 0}, {"pressure_kpa": -1}, {"temperature_k": float("nan")},
                       {"removal_fraction": 1.1}, {"co2_kg_per_person_day": -1}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                CabinConfig(**config)
        with self.assertRaises(ValueError):
            co2_percent_after(-1, 5)

    def test_integrated_balanced_case_and_provenance(self):
        samples = generate_scenario("co2_rise", cabin_config=CabinConfig(removal_fraction=1))
        self.assertTrue(all(s["environment"]["co2_percent"] == 0.1 for s in samples))
        self.assertEqual(samples[-1]["cabin_model"]["parameters"]["removal_fraction"], 1)
