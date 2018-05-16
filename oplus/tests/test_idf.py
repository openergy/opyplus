import unittest
import os

from oplus import Idf, BrokenIdfError, IsPointedError
from oplus.idf.record import Record
from oplus.configuration import CONF
from oplus.tests.util import TESTED_EPLUS_VERSIONS, eplus_tester


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

    def test_idf_call(self):
        for eplus_version in eplus_tester(self):
            qs = self.idfs_d[eplus_version]("Construction")
            self.assertEqual(
                {"R13WALL", "FLOOR", "ROOF31"},
                set([c["name"] for c in qs])
            )

    def test_qs_one(self):
        for eplus_version in eplus_tester(self):
            self.assertEqual(
                self.idfs_d[eplus_version]("BuildingSurface:Detailed").filter("naMe", "Zn001:Roof001").one["name"],
                "Zn001:Roof001"
            )

    def test_idf_add_object(self):
        for eplus_version in eplus_tester(self):
            sch_name = "NEW TEST SCHEDULE"
            sch = self.idfs_d[eplus_version].add_object(schedule_test_record_str % sch_name)
            self.assertTrue(isinstance(sch, Record))

    def test_multi_level_filter(self):
        for eplus_version in eplus_tester(self):
            # get all building surfaces that have a zone with Z-Origin 0
            simple_filter_l = []
            for bsd in self.idfs_d[eplus_version]("BuildingSurface:Detailed"):
                if bsd["Zone name"][4] == 0:
                    simple_filter_l.append(bsd)
            multi_filter_l = self.idfs_d[eplus_version]("BuildingSurface:Detailed")\
                .filter(("Zone Name", 4), 0).records
            self.assertEqual(simple_filter_l, multi_filter_l)


class DynamicIdfTest(unittest.TestCase):
    """
    The following tests modify the idf.
    """

    @staticmethod
    def get_idf():
        return Idf(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))

    def test_idf_add_record(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            sch_name = "NEW TEST SCHEDULE"
            idf.add_object(schedule_test_record_str % sch_name)
            self.assertEqual(idf("Schedule:Compact").filter("name", sch_name).one["name"], sch_name)

    def test_idf_remove_record(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            sch_name = "NEW TEST SCHEDULE"
            sch = idf.add_object(schedule_test_record_str % sch_name)
            idf.remove_object(sch)
            self.assertEqual(len(idf("Schedule:Compact").filter("name", sch_name)), 0)

    def test_idf_remove_record_raise(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            zone = idf("Zone").one
            self.assertRaises(IsPointedError, lambda: idf.remove_object(zone))

    def test_idf_remove_record_dont_raise(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            zone = idf("Zone").one
            idf.remove_object(zone, raise_if_pointed=False)
            self.assertEqual(len(idf("Zone")), 0)

    def test_pointing_records(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            zone = idf("Zone").one
            self.assertEqual(
                {
                    "Zn001:Wall001",
                    "Zn001:Wall002",
                    "Zn001:Wall003",
                    "Zn001:Wall004",
                    "Zn001:Flr001",
                    "Zn001:Roof001"
                },
                set([bsd["name"] for bsd in zone.pointing_records("BuildingSurface:Detailed")])
            )

    def test_pointed_records(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            bsd = idf("BuildingSurface:Detailed").filter("name", "Zn001:Wall001").one
            zone = idf("Zone").filter("name", "Main Zone").one
            self.assertEqual(bsd["zone name"], zone)
            self.assertEqual(bsd[3], zone)

    def test_idf_copy(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            old_name = "System Availability Schedule"
            old = idf("Schedule:Compact").filter("name", old_name).one
            new = old.copy()
            new_name = old_name + "- new"
            new["name"] = new_name
            self.assertNotEqual(old, new)

    def test_set_record_simple(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            new_name = "Fan Availability Schedule - 2"
            supply_fan = idf("Fan:ConstantVolume").filter("name", "Supply Fan").one
            supply_fan["availability schedule name"] = schedule_test_record_str % new_name
            # check set
            self.assertEqual(
                idf("Fan:ConstantVolume").filter("name", "Supply Fan").one["AvaiLABIlity schedule name"]["name"],
                new_name)

    def test_set_record_broken(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            supply_fan = idf("Fan:ConstantVolume").filter("name", "Supply Fan").one
            name = supply_fan["availability schedule name"]["name"]

            def raise_if_you_care():
                supply_fan["availability schedule name"] = schedule_test_record_str % name
            self.assertRaises(BrokenIdfError, raise_if_you_care)

    def test_set_record_broken_constructing_mode(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            supply_fan = idf("Fan:ConstantVolume").filter("name", "Supply Fan").one
            name = supply_fan["availability schedule name"]["name"]

            with self.assertRaises(BrokenIdfError):
                with idf.under_construction:
                    supply_fan["availability schedule name"] = schedule_test_record_str % name

    def test_extensible(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            sch = idf("Schedule:Compact").filter("name", "System Availability Schedule").one
            for i in range(1500):
                sch.add_field("12:00")
            self.assertEqual(sch[1300], "12:00")

    def test_pop_end(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            sch = idf("Schedule:Compact").filter("name", "System Availability Schedule").one
            ini_len = len(sch)
            self.assertEqual("1", sch.pop())
            self.assertEqual(ini_len-1, len(sch))

    def test_pop_middle(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            sch = idf("Schedule:Compact").filter("name", "System Availability Schedule").one

            # before pop
            self.assertEqual(
                """Schedule:Compact,
    System Availability Schedule,  ! - Name
    Any Number,                    ! - Schedule Type Limits Name
    THROUGH: 12/31,                ! - Field 1
    FOR: AllDays,                  ! - Field 2
    UNTIL: 24:00,                  ! - Field 3
    1;                             ! - Field 3
""",
                sch.to_str())

            # pop
            self.assertEqual("THROUGH: 12/31", sch.pop(2))

            # after pop
            self.assertEqual(
                """Schedule:Compact,
    System Availability Schedule,  ! - Name
    Any Number,                    ! - Schedule Type Limits Name
    FOR: AllDays,                  ! - Field 2
    UNTIL: 24:00,                  ! - Field 3
    1;                             ! - Field 3
""",
                sch.to_str())

    def test_pop_raises(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            sch = idf("Schedule:Compact").filter("name", "System Availability Schedule").one
            self.assertRaises(AssertionError, lambda: sch.pop(1))

    def test_cache_on_filter(self):
        for _ in eplus_tester(self):
            idf = self.get_idf()
            sch = idf("Schedule:Compact").filter("name", "System Availability Schedule").one
            self.assertTrue(len(idf._.cache) > 0)

            # clear
            idf.clear_cache()
            self.assertEqual(0, len(idf._.cache))

            # retry
            sch = idf("Schedule:Compact").filter("name", "System Availability Schedule").one
            self.assertTrue(len(idf._.cache) > 0)


class MiscellaneousIdfTest(unittest.TestCase):
    def test_simple_read(self):
        for _ in eplus_tester(self):
            for idf_name in ("4ZoneWithShading_Simple_1",):
                Idf(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", f"{idf_name}.idf"))

    def test_multiple_branch_links(self):
        for _ in eplus_tester(self):
            idf = Idf(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "5ZoneAirCooled.idf"))
            bl = idf("BranchList").filter("Name", "Heating Supply Side Branches").one
            b3 = idf("Branch").filter("Name", "Heating Supply Bypass Branch").one
            self.assertEqual(bl[3], b3)
