import unittest
import os
import tempfile

from oplus.configuration import CONFIG
from oplus.simulation import simulate
from oplus.eio import EIO

DEBUG_SIMUL_DIR_PATH = r"C:\Users\Geoffroy\Desktop\simul_dir"  # -> set to None to bypass


class AllExamplesShouldWork(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    """
    MAX_TESTS_NB = 500
    START_FILE_NUM = 0

    def test_no_errors(self):
        # !! CAN BE VERY LONG
        epw_path = os.path.join(CONFIG.eplus_base_dir_path, "WeatherData",
                                "USA_VA_Sterling-Washington.Dulles.Intl.AP.724030_TMY3.epw")
        idf_dir_path = os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles")
        test_num = 0
        for file_num, file_name in enumerate(os.listdir(idf_dir_path)):
            if file_num < self.START_FILE_NUM:
                continue
            base, ext = os.path.splitext(file_name)
            if ext == ".idf":
                with tempfile.TemporaryDirectory() as simulation_dir_path:
                    print("Simulating: %s" % file_name)
                    s = simulate(os.path.join(idf_dir_path, file_name), epw_path,
                                 simulation_dir_path if DEBUG_SIMUL_DIR_PATH is None else
                                 DEBUG_SIMUL_DIR_PATH)
                    if s.exists("eio"):
                        eio = EIO(s.path("eio"))  # raise error if problem
                        test_num += 1
            if test_num == self.MAX_TESTS_NB:
                break


class TestValues(unittest.TestCase):
    def test_1ZoneUncontrolled(self):
        idf_path = os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "1ZoneUncontrolled.idf")
        epw_path = r"C:\EnergyPlusV8-1-0\WeatherData\USA_FL_Tampa.Intl.AP.722110_TMY3.epw"

        with tempfile.TemporaryDirectory() as temp_dir_path:
            s = simulate(idf_path, epw_path, temp_dir_path if DEBUG_SIMUL_DIR_PATH is None else DEBUG_SIMUL_DIR_PATH)
            eio = s.eio

        self.assertEqual(float(eio.df("Site:GroundReflectance:SnowModifier").loc[0, "Normal"]), 1)
        df = eio.df("Material CTF Summary")
        self.assertEqual(df[df[df.columns[0]] == "R13LAYER"].iloc[0, 5], 2.291)
        self.assertEqual(eio.get_value("Material CTF Summary", 5, 0, "R13LAYER"), 2.291)
        self.assertEqual(eio.get_value("Material CTF Summary", "ThermalResistance {m2-K/w}", "Material Name",
                                       "R13LAYER"), 2.291)

        # print(eio("Construction CTF"))
        # print(eio("Material CTF Summary"))
        # print(eio("Zone Air Generic Contaminant Balance Simulation"))