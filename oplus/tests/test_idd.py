import unittest

from oplus.idd import *
from oplus.configuration import CONF

from oplus.tests.util import eplus_tester


class IDDTest(unittest.TestCase):
    def test_load(self):
        for _ in eplus_tester(self):
            IDD(path=os.path.join(CONF.eplus_base_dir_path, "Energy+.idd"))
