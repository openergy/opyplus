import unittest

from oplus.idd import *


EPLUS_720_IDD_PATH = r"C:\EnergyPlusV7-2-0\Energy+.idd"
EPLUS_810_IDD_PATH = r"C:\EnergyPlusV8-1-0\Energy+.idd"


class IDDTest(unittest.TestCase):
    def test_eplus720_parse(self):
        IDD(path=EPLUS_720_IDD_PATH)
        self.assertTrue(True)

    def test_eplus810_parse(self):
        IDD(path=EPLUS_810_IDD_PATH)
        self.assertTrue(True)

