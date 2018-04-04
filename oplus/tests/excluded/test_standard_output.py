import os
import unittest
import datetime as dt
import tempfile

from oplus.idf import IDF
from oplus.configuration import CONF as CONFIG
from oplus.simulation import simulate


class ZoneWithShadingSimple1(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    """
    idf_path = os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf")
    epw_path = os.path.join(CONFIG.eplus_base_dir_path, "WeatherData", "USA_CO_Golden-NREL.724666_TMY3.epw")

    def add_output(self, idf, time_step):
        idf.add_object("Output:Variable,*,Site Outdoor Air Drybulb Temperature,%s;" % time_step)

    def test_all_time_steps(self):
        """
        Detailed doesn't work, but not tested because not a priority. # todo: understand detailed
        """
        time_steps_l = ["TimeStep", "Hourly", "Daily", "Monthly", "RunPeriod"]
        for time_step in time_steps_l:
            with tempfile.TemporaryDirectory() as temp_dir_path:
                idf = IDF(self.idf_path)
                self.add_output(idf, time_step)
                s = simulate(idf, self.epw_path, temp_dir_path)
                self.assertIsNotNone(s.eso.df(time_step=time_step), "Problem for: '%s'." % time_step)

    def test_start_dt(self):
        with tempfile.TemporaryDirectory() as temp_dir_path:
            idf = IDF(self.idf_path)
            self.add_output(idf, "Hourly")
            s = simulate(idf, self.epw_path, temp_dir_path, simulation_control="RunPeriods")
            start_dt = dt.datetime(2000, 1, 1)
            self.assertEqual(s.eso.df(time_step="Hourly", start=start_dt).index[0], dt.datetime(2000, 1, 1, 1))