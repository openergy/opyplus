import unittest
import os

from tests.util import TESTED_EPLUS_VERSIONS, iter_eplus_versions

from oplus import Epm, BrokenEpmError, IsPointedError
from oplus.idf.record import Record
from oplus.configuration import CONF
from oplus import ObsoleteRecordError


class MiscellaneousIdfTest(unittest.TestCase):
    def test_simple_read(self):
        for _ in iter_eplus_versions(self):
            for idf_name in ("4ZoneWithShading_Simple_1",):
                Epm(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", f"{idf_name}.idf"))

    def test_multiple_branch_links(self):
        for _ in iter_eplus_versions(self):
            idf = Epm(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "5ZoneAirCooled.idf"))
            bl = idf.BranchList.one(lambda x: x.name == "heating supply side branches")
            b3 = idf.Branch.one(lambda x: x.name == "heating supply bypass branch")
            self.assertEqual(bl[3], b3)
