import unittest
import os

from tests.util import TESTED_EPLUS_VERSIONS, iter_eplus_versions

from oplus.epm.parse_idf import parse_idf
from oplus import CONF


class IdfParseTest(unittest.TestCase):
    def test_one_zone_evap(self):
        for eplus_version in TESTED_EPLUS_VERSIONS:
            with open(os.path.join(
                    CONF.eplus_base_dir_path,
                    "ExampleFiles",
                    "1ZoneEvapCooler.idf")) as f:
                json_data = parse_idf(f)

        # todo: test properly
