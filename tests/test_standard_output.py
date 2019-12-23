import os
import unittest
import datetime as dt

from opyplus import Simulation
from tests.util import iter_eplus_versions
from tests.resources import Resources


class StandardOutputTest(unittest.TestCase):
    # idf_path = os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf")
    # epw_path = os.path.join(CONFIG.eplus_base_dir_path, "WeatherData", "USA_CO_Golden-NREL.724666_TMY3.epw")

    def test_all_time_steps(self):
        for eplus_version in iter_eplus_versions(self):
            eplus_version_str = "-".join([str(v) for v in eplus_version])
            simulation_path = os.path.join(
                Resources.SimulationsOutputs.one_zone_uncontrolled,
                eplus_version_str
            )
            s = Simulation(simulation_path)

            for frequency in ["timestep", "hourly", "daily", "monthly", "annual", "run_period"]:
                df = s.get_out_eso().get_data(frequency=frequency)
                if frequency == "annual":
                    self.assertIsNone(df)
                    continue

                # check one day of data (15 min time step)
                self.assertEqual(
                    {
                        "timestep": 96,
                        "hourly": 24,
                        "daily": 1,
                        "monthly": 1,
                        "run_period": 1
                    }[frequency],
                    len(df)
                )

    @unittest.skip("not relevant")
    def test_start_dt(self):
        for eplus_version in iter_eplus_versions(self):
            eplus_version_str = "-".join([str(v) for v in eplus_version])
            simulation_path = os.path.join(
                Resources.SimulationsOutputs.one_zone_uncontrolled,
                eplus_version_str
            )
            s = Simulation(simulation_path)
            start_dt = dt.datetime(2000, 1, 1)
            self.assertEqual(
                dt.datetime(2000, 1, 1, 1),
                s.eso.get_df(time_step="Hourly", start=start_dt).index[0]
            )
