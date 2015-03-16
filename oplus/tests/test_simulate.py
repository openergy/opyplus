import unittest
import os
import tempfile

from oplus.idf import IDF
from oplus.epw import EPW
from oplus.standard_output import StandardOutputFile
from oplus.simulation import simulate
from oplus.configuration import CONFIG


class OneZoneEvapCooler(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    """
    idf = IDF(os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))
    epw = EPW(os.path.join(CONFIG.eplus_base_dir_path, "WeatherData", "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"))

    def test_simulation_control(self):
        for (simulation_control, expected_environments) in (
                (None, {"RunPeriod", "SummerDesignDay", "WinterDesignDay"}),
                ("RunPeriods", {"RunPeriod"}),
                ("Sizing", {"SummerDesignDay", "WinterDesignDay"})
        ):
            with tempfile.TemporaryDirectory() as dir_path:
                s = simulate(self.idf, self.epw, dir_path, simulation_control=simulation_control)

                self.assertIsInstance(s.eso, StandardOutputFile)
                self.assertIsInstance(s.mtr, StandardOutputFile)
                self.assertEqual(set(s.eso.environments), expected_environments)
                self.assertEqual(set(s.mtr.environments), expected_environments)