import unittest
import os

from oplus.idd.idd import Idd
from oplus.configuration import CONF

from oplus.tests.util import iter_eplus_versions


class IddTest(unittest.TestCase):
    def test_load(self):
        for _ in iter_eplus_versions(self):
            Idd(path_or_key=os.path.join(CONF.eplus_base_dir_path, "Energy+.idd"))

    def test_eq_idd(self):
        idd1 = Idd()
        idd2 = Idd()
        self.assertEqual(idd1, idd2)
