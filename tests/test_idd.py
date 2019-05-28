import unittest

from oplus.idd.idd import Idd

from tests.util import iter_eplus_versions


class IddTest(unittest.TestCase):
    def test_load(self):
        for _ in iter_eplus_versions(self):
            idd = Idd()


