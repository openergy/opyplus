import unittest
import os

from oplus.idf import IDF
from oplus.epw import EPW
from oplus.standard_output import StandardOutputFile
from oplus.simulate import Simulation
from oplus.configuration import CONFIG


class OneZoneEvapCooler(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    """
    idf = IDF(os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))
    epw = EPW(r"C:\EnergyPlusV8-1-0\WeatherData\USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw")

    def test_temp_dir(self):
        s = Simulation(self.idf, epw_or_path=self.epw)
        with s:
            temp_dir_path = s.simulation_dir_path

        # check that temp dir has been deleted
        self.assertFalse(os.path.exists(temp_dir_path), "Directory has not been deleted: '%s'." % temp_dir_path)

    def test_temp_dir_with_error(self):
        s = Simulation(self.idf, epw_or_path=self.epw)

        temp_dir_path = None
        try:
            with s:
                temp_dir_path = s.simulation_dir_path
                s.run()
                raise NotImplementedError()
        except NotImplementedError:
            pass
        self.assertFalse(os.path.exists(temp_dir_path), "Directory has not been deleted: '%s'." % temp_dir_path)
        self.assertIsInstance(s.err, str)

    def test_base_files_are_not_modified(self):
        s = Simulation(self.idf, epw_or_path=self.epw)
        with s:
            self.assertFalse(s.idf is self.idf)
            self.assertFalse(s.epw is self.epw)

    def test_run_simulate_size(self):
        for (method_name, expected_environments) in (
                ("run", {"RunPeriod", "SummerDesignDay", "WinterDesignDay"}),
                ("simulate", {"RunPeriod"}),
                ("size", {"SummerDesignDay", "WinterDesignDay"})
        ):

            s = Simulation(self.idf, epw_or_path=self.epw)

            with s:
                getattr(s, method_name)()
                self.assertIsInstance(s.eso, StandardOutputFile)
                self.assertIsInstance(s.mtr, StandardOutputFile)
                self.assertEqual(set(s.eso.environments), expected_environments)
                self.assertEqual(set(s.mtr.environments), expected_environments)