import unittest
import os

import opyplus as op

from tests.util import iter_eplus_versions


class IddTest(unittest.TestCase):
    def test_load(self):
        for _ in iter_eplus_versions(self):
            idd = op.Idd()

    def test_on_off_schedule_type_limit(self):
        for eplus_version in iter_eplus_versions(self):
            if eplus_version >= (9, 2, 0):
                epm = op.Epm(idd_or_version=eplus_version)  # empty epm
                epm.Schedule_Compact.add(
                    name="test_on_off",
                    schedule_type_limit_names="on/off",
                    field_1="through: 12/31",
                    field_2="for: alldays",
                    field_3="until: 24:00",
                    field_4="1"
                )


