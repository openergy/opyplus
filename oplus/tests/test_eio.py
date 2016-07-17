import unittest
import os
import tempfile

from oplus.configuration import CONF
from oplus.simulation import simulate

DEBUG_SIMUL_DIR_PATH = None  # r"C:\Users\Geoffroy\Desktop\simul_dir"  # -> set to None to bypass


class TestValues(unittest.TestCase):
    def test_1ZoneUncontrolled(self):
        idf_path = os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneUncontrolled.idf")
        epw_path = os.path.join(CONF.eplus_base_dir_path, "WeatherData", "USA_FL_Tampa.Intl.AP.722110_TMY3.epw")

        with tempfile.TemporaryDirectory() as temp_dir_path:
            s = simulate(idf_path, epw_path, temp_dir_path if DEBUG_SIMUL_DIR_PATH is None else DEBUG_SIMUL_DIR_PATH)
            eio = s.eio

        self.assertEqual(float(eio.df("Site:GroundReflectance:SnowModifier").loc[0, "Normal"]), 1)
        df = eio.df("Material CTF Summary")
        self.assertEqual(float(df[df[df.columns[0]] == "R13LAYER"].iloc[0, 5]), 2.291)
        self.assertEqual(float(eio.get_value("Material CTF Summary", 5, 0, "R13LAYER")), 2.291)
        self.assertEqual(float(eio.get_value("Material CTF Summary", "ThermalResistance {m2-K/w}", "Material Name",
                                             "R13LAYER")), 2.291)

        # print(eio("Construction CTF"))
        # print(eio("Material CTF Summary"))
        # print(eio("Zone Air Generic Contaminant Balance Simulation"))