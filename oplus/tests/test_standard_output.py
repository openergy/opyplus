import os
import unittest
import datetime as dt

from oplus.idf import IDF
from oplus.epw import EPW
from oplus.configuration import CONFIG
from oplus.simulate import Simulation


class ZoneWithShadingSimple1(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    """
    idf = IDF(os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf"))
    epw = EPW(os.path.join(CONFIG.eplus_base_dir_path, "Weatherdata", "USA_CO_Golden-NREL.724666_TMY3.epw"))

    @classmethod
    def setUpClass(cls):
        for out in cls.idf("Output:Variable"):
            cls.idf.remove_object(out)

    def test_all_time_steps(self):
        """
        Detailed doesn't work, but not tested because not a priority. # todo: understand detailed
        """
        s = Simulation(self.idf, self.epw)
        # with s:
        # # print(len(s.idf("SimulationControl")))
        time_steps_l = ["Timestep", "Hourly", "Daily", "Monthly", "RunPeriod"]

        with s:
            for time_step in time_steps_l:
                s.idf.add_object("Output:Variable,*,Site Outdoor Air Drybulb Temperature,%s;" % time_step)
            s.simulate()
            for time_step in time_steps_l:
                self.assertIsNotNone(s.eso.df(time_step=time_step), "Problem for: '%s'." % time_step)

    def test_start_dt(self):
        s = Simulation(self.idf, self.epw)
        with s:
            s.simulate()
            start_dt = dt.datetime(2000, 1, 1)
            self.assertEqual(s.eso.df(time_step="Hourly", start=start_dt).index[0], dt.datetime(2000, 1, 1, 1))




