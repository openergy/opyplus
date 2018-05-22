import os
import unittest
import datetime as dt

from oplus import Simulation, CONF as CONFIG
from oplus.tests.util import iter_eplus_versions, RESOURCES_DIR_PATH


class StandardOutputTest(unittest.TestCase):
    idf_path = os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf")
    epw_path = os.path.join(CONFIG.eplus_base_dir_path, "WeatherData", "USA_CO_Golden-NREL.724666_TMY3.epw")

    def test_all_time_steps(self):
        """
        Detailed doesn't work, but not tested because not a priority. # todo: understand detailed
        """
        for eplus_version in iter_eplus_versions(self):
            eplus_version_str = "-".join([str(v) for v in eplus_version])
            simulation_path = os.path.join(
                RESOURCES_DIR_PATH,
                "simulations-outputs",
                "one_zone_uncontrolled",
                eplus_version_str
            )

            for time_step in ["TimeStep", "Hourly", "Daily", "Monthly", "RunPeriod"]:
                s = Simulation(simulation_path)
                df = s.eso.df(time_step=time_step)
                # check one day of data (15 min time step)
                self.assertEqual(
                    {
                        "TimeStep": 96,
                        "Hourly": 24,
                        "Daily": 1,
                        "Monthly": 1,
                        "RunPeriod": 1
                    }[time_step],
                    len(df)
                )

    def test_start_dt(self):
        for eplus_version in iter_eplus_versions(self):
            eplus_version_str = "-".join([str(v) for v in eplus_version])
            simulation_path = os.path.join(
                RESOURCES_DIR_PATH,
                "simulations-outputs",
                "one_zone_uncontrolled",
                eplus_version_str
            )
            s = Simulation(simulation_path)
            start_dt = dt.datetime(2000, 1, 1)
            self.assertEqual(
                dt.datetime(2000, 1, 1, 1),
                s.eso.df(time_step="Hourly", start=start_dt).index[0]
            )
