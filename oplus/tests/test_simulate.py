import unittest
import os
import tempfile
import io

from oplus import simulate, CONF, Idf
from oplus.tests.util import iter_eplus_versions
from oplus.idd.idd import Idd


class SimulateTest(unittest.TestCase):
    """
    we test everything in one simulation, for performance reasons
    """
    def test_simulate(self):
        for eplus_version in iter_eplus_versions(self):
            # prepare paths
            idf_path = os.path.join(
                CONF.eplus_base_dir_path,
                "ExampleFiles",
                "1ZoneEvapCooler.idf"
            )
            epw_path = os.path.join(
                CONF.eplus_base_dir_path,
                "WeatherData",
                "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
            )

            # prepare a quick simulation
            idf = Idf(idf_path)
            sc = idf["SimulationControl"].one()
            sc["Run Simulation for Sizing Periods"] = "No"
            rp = idf["RunPeriod"].one()
            rp["End Month"] = 1
            rp["End Day of Month"] = 1

            # prepare outputs
            out_f = io.StringIO()
            err_f = io.StringIO()

            # simulate
            with tempfile.TemporaryDirectory() as dir_path:
                s = simulate(
                    idf,
                    epw_path,
                    dir_path,
                    stdout=out_f,
                    stderr=err_f,
                    beat_freq=0.1
                )

                # check one day output
                eso_df = s.eso.df()
                self.assertEqual(24, len(eso_df))

            # check err (manage differences between eplus versions)
            err_out = err_f.getvalue()
            self.assertTrue(
                (err_out == "") or
                ("EnergyPlus Completed Successfully.\n" in err_out)
            )
            # check beat
            out_str = out_f.getvalue()
            self.assertIn("subprocess is still running", out_str)

            # check stdout
            out_str = out_str.replace("subprocess is still running\n", "")
            self.assertGreater(len(out_str.split("\n")), 15)  # check that more than 15 lines

    def test_simulate_with_custom_idd(self):
        for eplus_version in iter_eplus_versions(self):
            default_idd_path = Idd.get_idd_path()
            dirname, basename = os.path.split(default_idd_path)

            with tempfile.TemporaryDirectory() as dir_path:
                # path
                new_idd_path = os.path.join(dir_path, f"~{basename}")

                # create empty file
                open(new_idd_path, "w").close()
                self.assertTrue(os.path.isfile(new_idd_path))

                # prepare idf and epw paths
                idf_path = os.path.join(
                    CONF.eplus_base_dir_path,
                    "ExampleFiles",
                    "1ZoneEvapCooler.idf"
                )
                epw_path = os.path.join(
                    CONF.eplus_base_dir_path,
                    "WeatherData",
                    "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
                )

                # prepare a quick simulation
                idf = Idf(idf_path)
                sc = idf["SimulationControl"].one()
                sc["Run Simulation for Sizing Periods"] = "No"
                rp = idf["RunPeriod"].one()
                rp["End Month"] = 1
                rp["End Day of Month"] = 1

                # prepare outputs
                out_f = io.StringIO()
                err_f = io.StringIO()

                # simulate with empty idd -> must raise
                simulate(
                    idf,
                    epw_path,
                    dir_path,
                    stdout=out_f,
                    stderr=err_f,
                    beat_freq=0.1,
                    idd_or_path_or_key=new_idd_path
                )
                self.assertEqual(
                    err_f.getvalue().strip("\n"),
                    "Program terminated: EnergyPlus Terminated--Error(s) Detected."
                )

                # simulate with good idd -> check that works
                s = simulate(
                    idf,
                    epw_path,
                    dir_path,
                    stdout=out_f,
                    stderr=err_f,
                    beat_freq=0.1,
                    idd_or_path_or_key=default_idd_path
                )

                # check one day output
                eso_df = s.eso.df()
                self.assertEqual(24, len(eso_df))

                # check err (manage differences between eplus versions)
                err_out = err_f.getvalue()
                self.assertTrue(
                    (err_out == "") or
                    ("EnergyPlus Completed Successfully.\n" in err_out)
                )
                # check beat
                out_str = out_f.getvalue()
                self.assertIn("subprocess is still running", out_str)

                # check stdout
                out_str = out_str.replace("subprocess is still running\n", "")
                self.assertGreater(len(out_str.split("\n")), 15)  # check that more than 15 lines
