import os
import unittest

from oplus.idf import IDF
from oplus.epw import EPW
from oplus.configuration import CONFIG
from oplus.simulate import Simulation


class ZoneWithShadingSimple1(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    """
    idf = IDF(os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf"))
    epw = EPW(r"C:\EnergyPlusV8-1-0\WeatherData\USA_CO_Golden-NREL.724666_TMY3.epw")

    @classmethod
    def setUpClass(cls):
        for out in cls.idf("Output:Variable"):
            cls.idf.remove_object(out)

    def test_all_time_steps(self):
        s = Simulation(self.idf, self.epw)  # todo: -> the problem seems to come from Lead Input; Data Dictionary; ...
        with s:
        #     for ref in sorted([o.ref for o in s.idf._.objects_l]):
        #         print(ref)
            s.idf.save_as(r"C:\Users\Geoffroy\Desktop\test\yo.idf")
        # print(len(s.idf("SimulationControl")))
        # time_steps_l = ["Detailed", "Timestep", "Hourly", "Daily", "Monthly", "RunPeriod"]
        #
        # with s:
        #     for time_step in time_steps_l:
        #         s.idf.add_object("Output:Variable,*,Site Outdoor Air Drybulb Temperature,%s;" % time_step)
        #     s.simulate()
        #     for time_step in time_steps_l:
        #         self.assertIsNotNone(s.eso.df(time_step=time_step))



