import unittest
import os

from oplus.idf.idd import Idd
from oplus.configuration import CONF

from tests.util import iter_eplus_versions


class IddTest(unittest.TestCase):
    def test_load(self):
        for _ in iter_eplus_versions(self):
            idd = Idd()


