import unittest

import oplus as op

from tests.util import iter_eplus_versions


class EpmNoTemplateTest(unittest.TestCase):
    def test_rename(self):
        for _ in iter_eplus_versions(self):
            epm = op.Epm(check_required=False)
            # create zone
            zone = epm.zone.add(dict(name="z"))

            # create and attach bsd
            bsd = epm.BuildingSurface_Detailed.add(dict(name="bsd", zone_name=zone))

            # check attached
            self.assertEqual(zone, bsd.zone_name)

            # rename zone
            new_name = "new_name"
            zone.name = new_name

            # check name changed
            self.assertEqual(new_name, zone.name)

            # check link was not broken
            self.assertEqual(zone, bsd.zone_name)

    def test_check_length(self):
        for _ in iter_eplus_versions(self):
            # without check
            epm = op.Epm(check_length=False)

            # add big zone
            epm.zone.add(dict(name="a"*500))

            # with check
            epm = op.Epm()
            self.assertRaises(op.FieldValidationError, epm.zone.add, dict(name="a"*500))
