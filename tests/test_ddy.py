import unittest
import os

from tests.util import iter_eplus_versions
from opyplus import Ddy
from opyplus.compatibility import get_eplus_base_dir_path
from opyplus import CONF


class DdyTest(unittest.TestCase):
    def test_ddy_generation(self):
        # check that a ddy can be correctly loaded with designdays
        for eplus_version in iter_eplus_versions(self):
            with open(
                    os.path.join(
                        get_eplus_base_dir_path(eplus_version),
                        "WeatherData",
                        "USA_CA_San.Francisco.Intl.AP.724940_TMY3.ddy"),
                    encoding=CONF.encoding
            ) as f:
                ddy = Ddy.from_ddy(f)
        design_day_table = ddy.sizingperiod_designday
