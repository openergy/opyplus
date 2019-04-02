import unittest
import os

from tests.util import iter_eplus_versions, RESOURCES_DIR_PATH
from oplus import Simulation


class TestValues(unittest.TestCase):
    def test_values(self):
        for eplus_version in iter_eplus_versions(self):
            if eplus_version == (9, 0, 1):  # todo: make 9.0.1 tests !!
                continue
            version_str = "-".join([str(v) for v in eplus_version])
            s = Simulation(os.path.join(
                RESOURCES_DIR_PATH,
                "simulations-outputs",
                "one_zone_uncontrolled",
                version_str
            ))
            eio = s.eio

            self.assertEqual(
                float(eio.get_df("Site:GroundReflectance:SnowModifier").loc[0, "Normal"]),
                1
            )
            df = eio.get_df("Material CTF Summary")

            self.assertEqual(
                float(df[df[df.columns[0]] == "R13LAYER"].iloc[0, 5]),
                2.291
            )
            self.assertEqual(
                float(eio.get_value("Material CTF Summary", 5, 0, "R13LAYER")),
                2.291
            )
            self.assertEqual(
                float(eio.get_value(
                    "Material CTF Summary",
                    "ThermalResistance {m2-K/w}",
                    "Material Name",
                    "R13LAYER")
                ),
                2.291
            )
