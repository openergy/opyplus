import unittest
import os

from oplus import Simulation
from tests.util import iter_eplus_versions
from tests.resources import Resources



class ErrTest(unittest.TestCase):
    def test_err(self):
        for eplus_version in iter_eplus_versions(self):
            version_str = "-".join([str(v) for v in eplus_version])
            s = Simulation(os.path.join(
                Resources.SimulationsOutputs.one_zone_uncontrolled,
                version_str
            ))
            self.assertIsNotNone(s.get_out_err())
