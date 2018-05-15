import unittest
import os

from oplus.idd.idd import Idd
from oplus.configuration import CONF

from oplus.tests.util import eplus_tester


class IddTest(unittest.TestCase):
    def test_load(self):
        for _ in eplus_tester(self):
            Idd(path=os.path.join(CONF.eplus_base_dir_path, "Energy+.idd"))
