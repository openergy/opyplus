import unittest
import os

from oplus import Idf, BrokenIdfError, IsPointedError
from oplus.idf.record import Record
from oplus.configuration import CONF
from oplus.tests.util import TESTED_EPLUS_VERSIONS, iter_eplus_versions
from oplus import ObsoleteRecordError


schedule_test_record_str = """Schedule:Compact,
    %s,  !- Name
    Any Number,              !- Schedule Type Limits Name
    THROUGH: 12/31,          !- Field 1
    FOR: AllDays,            !- Field 2
    UNTIL: 12:00,1,          !- Field 3
    UNTIL: 24:00,0;          !- Field 5"""


class StaticIdfTest(unittest.TestCase):
    """
    Only tests that do not modify Idf (avoid loading idf several times) - else use DynamicIdfTest.
    """
    idfs_d = None

    @classmethod
    def setUpClass(cls):
        cls.idfs_d = {}
        for eplus_version in TESTED_EPLUS_VERSIONS:
            CONF.eplus_version = eplus_version
            cls.idfs_d[eplus_version] = Idf(os.path.join(
                CONF.eplus_base_dir_path,
                "ExampleFiles",
                "1ZoneEvapCooler.idf")
            )

    @classmethod
    def tearDownClass(cls):
        del cls.idfs_d

    def test_get_table(self):
        for eplus_version in iter_eplus_versions(self):
            table = self.idfs_d[eplus_version].Construction
            self.assertEqual(
                {"r13wall", "floor", "roof31"},
                set([c.name for c in table.select()])
            )

    def test_qs_one(self):
        for eplus_version in iter_eplus_versions(self):
            self.assertEqual(
                self.idfs_d[eplus_version].BuildingSurface_Detailed.one(
                    lambda x: x.name == "zn001:roof001").name,
                "zn001:roof001"
            )

    def test_idf_add_object(self):
        for eplus_version in iter_eplus_versions(self):
            sch_name = "NEW TEST SCHEDULE"
            sch = self.idfs_d[eplus_version].add_from_string(schedule_test_record_str % sch_name)
            self.assertTrue(isinstance(sch, Record))

    def test_multi_level_filter(self):
        for eplus_version in iter_eplus_versions(self):
            # get all building surfaces that have a zone with Z-Origin 0
            simple_filter_l = []
            for bsd in self.idfs_d[eplus_version].BuildingSurface_Detailed.select():
                if bsd.zone_name[4] == 0:
                    simple_filter_l.append(bsd)
            multi_filter_l = list(
                self.idfs_d[eplus_version].BuildingSurface_Detailed.select(
                    lambda x: x.zone_name[4] == 0
                )
            )
            self.assertEqual(simple_filter_l, multi_filter_l)


class DynamicIdfTest(unittest.TestCase):
    """
    The following tests modify the idf.
    """

    @staticmethod
    def get_idf():
        return Idf(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))

    def test_idf_add_record(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            sch_name = "new test schedule"
            idf.add_from_string(schedule_test_record_str % sch_name)
            self.assertEqual(idf.Schedule_Compact.one(lambda x: x.name == sch_name).name, sch_name)

    def test_idf_remove_record(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            sch_name = "NEW TEST SCHEDULE"
            sch = idf.add_from_string(schedule_test_record_str % sch_name)
            idf.remove(sch)

            # check removed
            self.assertEqual(len(idf.Schedule_Compact.select(lambda x: x.name == sch_name)), 0)

            # check obsolete
            self.assertRaises(ObsoleteRecordError, lambda: print(sch))

    def test_idf_remove_record_raise(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            zone = idf.Zone.one()
            self.assertRaises(IsPointedError, lambda: idf.remove(zone))

    def test_idf_unlink_and_remove(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            zone = idf.Zone.one()
            zone.unlink_pointing_records()
            idf.remove(zone)
            self.assertEqual(len(idf.Zone.select()), 0)

    def test_pointing_records(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            zone = idf.Zone.one()
            self.assertEqual(
                {
                    "zn001:wall001",
                    "zn001:wall002",
                    "zn001:wall003",
                    "zn001:wall004",
                    "zn001:flr001",
                    "zn001:roof001"
                },
                set([bsd.name for bsd in zone.get_pointing_records().BuildingSurface_Detailed])
            )

    def test_pointed_records(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            bsd = idf.BuildingSurface_Detailed.one(lambda x: x.name == "zn001:wall001")
            zone = idf.Zone.one(lambda x: x.name == "main zone")
            construction = idf.Construction.one(lambda x: x.name == "r13wall")

            # single pointing field
            self.assertEqual(bsd.zone_name, zone)
            self.assertEqual(bsd[3], zone)

            # get all pointed
            pointing = bsd.get_pointed_records()
            self.assertEqual(
                (zone, construction),
                (pointing.zone.one(), pointing.construction.one())
            )

    def test_copy_record(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            old_name = "system availability schedule"
            old = idf.Schedule_Compact.one(lambda x: x.name == old_name)
            new = old.copy()
            new_name = old_name + "- new"
            new.name = new_name
            self.assertNotEqual(old, new)

    def test_set_record_simple(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            new_name = "fan availability schedule - 2"
            supply_fan = idf.Fan_ConstantVolume.one(lambda x: x.name == "supply fan")
            supply_fan.availability_schedule_name = schedule_test_record_str % new_name
            # check set
            self.assertEqual(
                idf.Fan_ConstantVolume.one(
                    lambda x: x.name == "supply fan"
                ).availability_schedule_name.name,
                new_name
            )

    def test_set_record_wrong_type(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()

            def set_field():
                idf.building.one().north_axis = "I'm a text, not a real"

            self.assertRaises(ValueError, set_field)

    def test_set_record_broken(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            supply_fan = idf.Fan_ConstantVolume.one(lambda x: x.name == "supply fan")
            name = supply_fan.availability_schedule_name.name

            def raise_if_you_care():
                supply_fan.availability_schedule_name = schedule_test_record_str % name
            self.assertRaises(BrokenIdfError, raise_if_you_care)

    def test_set_record_broken_constructing_mode(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            supply_fan = idf.Fan_ConstantVolume.one(lambda x: x.name == "supply fan")
            name = supply_fan.availability_schedule_name.name

            with self.assertRaises(BrokenIdfError):
                with idf.is_under_construction():
                    supply_fan.availability_schedule_name = schedule_test_record_str % name

    def test_extensible(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            sch = idf.Schedule_Compact.one(lambda x: x.name == "system availability schedule")
            for i in range(1500):
                sch.add_field("12:00")
            self.assertEqual(sch[1300], "12:00")

    def test_pop_end(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            sch = idf.Schedule_Compact.one(lambda x: x.name == "system availability schedule")
            ini_len = len(sch)
            self.assertEqual("1", sch.pop())
            self.assertEqual(ini_len-1, len(sch))

    def test_pop_middle(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            sch = idf.Schedule_Compact.one(lambda x: x.name == "system availability schedule")

            # before pop
            self.assertEqual(
                """Schedule:Compact,
    system availability schedule,  ! - Name
    any number,                    ! - Schedule Type Limits Name
    through: 12/31,                ! - Field 1
    for: alldays,                  ! - Field 2
    until: 24:00,                  ! - Field 3
    1;                             ! - Field 3
""",
                sch.to_str())

            # pop
            self.assertEqual("through: 12/31", sch.pop(2))

            # after pop
            self.assertEqual(
                """Schedule:Compact,
    system availability schedule,  ! - Name
    any number,                    ! - Schedule Type Limits Name
    for: alldays,                  ! - Field 2
    until: 24:00,                  ! - Field 3
    1;                             ! - Field 3
""",
                sch.to_str())

    def test_pop_raises(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            sch = idf.Schedule_Compact.one(lambda x: x.name == "system availability schedule")
            self.assertRaises(RuntimeError, lambda: sch.pop(1))

    def test_cache_on_filter(self):
        for _ in iter_eplus_versions(self):
            # load idf
            idf = self.get_idf()

            # check that cache is empty
            nb = len(idf._dev_cache)
            self.assertEqual(0, nb)

            # perform request
            idf.Schedule_Compact.one(lambda x: x.name == "system availability schedule")
            nb = len(idf._dev_cache)

            # check cache went up, and hits are 0
            self.assertTrue(nb > 0)
            self.assertEqual([0]*nb, [v["hits"] for v in idf._dev_cache.values()])

            # retry
            idf.Schedule_Compact.one(lambda x: x.name == "system availability schedule")

            # check cache didn't go up, and hits are 1
            self.assertEqual(nb, len(idf._dev_cache))
            self.assertEqual([1] * nb, [v["hits"] for v in idf._dev_cache.values()])

            # clear
            idf._dev_clear_cache()

            # check cache was cleared
            self.assertEqual(0, len(idf._dev_cache))


class MiscellaneousIdfTest(unittest.TestCase):
    def test_simple_read(self):
        for _ in iter_eplus_versions(self):
            for idf_name in ("4ZoneWithShading_Simple_1",):
                Idf(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", f"{idf_name}.idf"))

    def test_multiple_branch_links(self):
        for _ in iter_eplus_versions(self):
            idf = Idf(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "5ZoneAirCooled.idf"))
            bl = idf.BranchList.one(lambda x: x.name == "heating supply side branches")
            b3 = idf.Branch.one(lambda x: x.name == "heating supply bypass branch")
            self.assertEqual(bl[3], b3)
