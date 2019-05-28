import unittest
import os

from tests.util import iter_eplus_versions

from oplus.epm.parse_idf import parse_idf
from oplus.compatibility import get_eplus_base_dir_path
from oplus import CONF


class IdfParseTest(unittest.TestCase):
    def test_one_zone_evap(self):
        for eplus_version in iter_eplus_versions(self):
            with open(os.path.join(
                    get_eplus_base_dir_path(eplus_version),
                    "ExampleFiles",
                    "1ZoneEvapCooler.idf")) as f:
                json_data = parse_idf(f)

        # todo: test properly
