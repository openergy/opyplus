import unittest
import os
import logging

from oplus.idf import IDF, IDFObject, IDFError, CacheKey
from oplus.util import CachingNotAllowedError
from oplus.idf import BrokenIDFError, IsPointedError
from oplus.configuration import CONF


logger = logging.getLogger(__name__)


schedule_test_object_str = """Schedule:Compact,
    %s,  !- Name
    Any Number,              !- Schedule Type Limits Name
    THROUGH: 12/31,          !- Field 1
    FOR: AllDays,            !- Field 2
    UNTIL: 12:00,1,          !- Field 3
    UNTIL: 24:00,0;          !- Field 5"""


class OneZoneEvapCooler(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    !!! Only tests that do not modify IDF (avoid loading idf several times) - else use OneZoneEvapCoolerDynamic.
    """
    idf = None

    @classmethod
    def setUpClass(cls):
        cls.idf = IDF(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))

    @classmethod
    def tearDownClass(cls):
        del cls.idf

    def test_idf_call(self):
        qs = self.idf("Construction")
        self.assertEqual({"R13WALL", "FLOOR", "ROOF31"}, set([c["name"] for c in qs]))

    def test_qs_one(self):
        self.assertEqual(self.idf("BuildingSurface:Detailed").filter("naMe", "Zn001:Roof001").one["name"],
                         "Zn001:Roof001")

    def test_idf_add_object(self):
        sch_name = "NEW TEST SCHEDULE"
        sch = self.idf.add_object(schedule_test_object_str % sch_name)
        self.assertTrue(isinstance(sch, IDFObject))

    def test_multi_level_filter(self):
        # get all building surfaces that have a zone with Z-Origin 0
        simple_filter_l = []
        for bsd in self.idf("BuildingSurface:Detailed"):
            if bsd["Zone name"][4] == 0:
                simple_filter_l.append(bsd)
        multi_filter_l = self.idf("BuildingSurface:Detailed").filter(("Zone Name", 4), 0).objects_l
        self.assertEqual(simple_filter_l, multi_filter_l)


class OneZoneEvapCoolerDynamic(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    Here are tests that modify idf.
    """
    idf = None

    def setUp(self):
        self.idf = IDF(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))

    @classmethod
    def tearDownClass(cls):
        del cls.idf

    def test_idf_add_object(self):
        sch_name = "NEW TEST SCHEDULE"
        self.idf.add_object(schedule_test_object_str % sch_name)
        self.assertEqual(self.idf("Schedule:Compact").filter("name", sch_name).one["name"], sch_name)

    def test_idf_remove_object(self):
        sch_name = "NEW TEST SCHEDULE"
        sch = self.idf.add_object(schedule_test_object_str % sch_name)
        self.idf.remove_object(sch)
        self.assertEqual(len(self.idf("Schedule:Compact").filter("name", sch_name)), 0)

    def test_idf_remove_object_raise(self):
        zone = self.idf("Zone").one
        self.assertRaises(IsPointedError, lambda: self.idf.remove_object(zone))

    def test_idf_remove_object_dont_raise(self):
        zone = self.idf("Zone").one
        self.idf.remove_object(zone, raise_if_pointed=False)
        self.assertEqual(len(self.idf("Zone")), 0)

    def test_pointing_objects(self):
        zone = self.idf("Zone").one
        self.assertEqual({"Zn001:Wall001", "Zn001:Wall002", "Zn001:Wall003", "Zn001:Wall004", "Zn001:Flr001",
                          "Zn001:Roof001"},
                         set([bsd["name"] for bsd in zone.pointing_objects("BuildingSurface:Detailed")]))

    def test_pointed_objects(self):
        bsd = self.idf("BuildingSurface:Detailed").filter("name", "Zn001:Wall001").one
        zone = self.idf("Zone").filter("name", "Main Zone").one
        self.assertEqual(bsd["zone name"], zone)
        self.assertEqual(bsd[3], zone)

    def test_idf_copy(self):
        old_name = "System Availability Schedule"
        old = self.idf("Schedule:Compact").filter("name", old_name).one
        new = old.copy()
        new_name = old_name + "- new"
        new["name"] = new_name
        self.assertNotEqual(old, new)

    def test_set_object_simple(self):
        new_name = "Fan Availability Schedule - 2"
        supply_fan = self.idf("Fan:ConstantVolume").filter("name", "Supply Fan").one
        supply_fan["availability schedule name"] = schedule_test_object_str % new_name
        # check set
        self.assertEqual(
            self.idf("Fan:ConstantVolume").filter("name", "Supply Fan").one["AvaiLABIlity schedule name"]["name"],
            new_name)

    def test_set_object_broken(self):
        supply_fan = self.idf("Fan:ConstantVolume").filter("name", "Supply Fan").one
        name = supply_fan["availability schedule name"]["name"]

        def raise_if_you_care():
            supply_fan["availability schedule name"] = schedule_test_object_str % name
        self.assertRaises(BrokenIDFError, raise_if_you_care)

    def test_set_object_broken_constructing_mode(self):
        supply_fan = self.idf("Fan:ConstantVolume").filter("name", "Supply Fan").one
        name = supply_fan["availability schedule name"]["name"]

        with self.assertRaises(BrokenIDFError):
            with self.idf.under_construction:
                supply_fan["availability schedule name"] = schedule_test_object_str % name

    def test_extensible(self):
        sch = self.idf("Schedule:Compact").filter("name", "System Availability Schedule").one
        for i in range(1500):
            sch.add_field("12:00")
        self.assertEqual(sch[1300], "12:00")

    @unittest.skip("skipped but must be fixed !!!")
    def test_big_extensible(self):
        """
        Doesn't work but bypassed !!! todo: repair

        """
        sch = self.idf("Schedule:Compact").filter("name", "System Availability Schedule").one
        for i in range(4560):  # 4500 is the limit of idd
            sch.add_field("12:00")
        self.assertEqual(4560, len(sch))

    def test_pop_end(self):
        sch = self.idf("Schedule:Compact").filter("name", "System Availability Schedule").one
        ini_len = len(sch)
        self.assertEqual("1", sch.pop())
        self.assertEqual(ini_len-1, len(sch))

    def test_pop_middle(self):
        sch = self.idf("Schedule:Compact").filter("name", "System Availability Schedule").one

        self.assertEqual(sch.to_str(), """Schedule:Compact,
    System Availability Schedule,  ! - Name
    Any Number,                    ! - Schedule Type Limits Name
    THROUGH: 12/31,                ! - Field 1
    FOR: AllDays,                  ! - Field 2
    UNTIL: 24:00,                  ! - Field 3
    1;                             ! - Field 3
""")

        self.assertEqual("THROUGH: 12/31", sch.pop(2))
        self.assertEqual(sch.to_str(), """Schedule:Compact,
    System Availability Schedule,  ! - Name
    Any Number,                    ! - Schedule Type Limits Name
    FOR: AllDays,                  ! - Field 2
    UNTIL: 24:00,                  ! - Field 3
    1;                             ! - Field 3
""")

    def test_pop_raises(self):
        sch = self.idf("Schedule:Compact").filter("name", "System Availability Schedule").one
        self.assertRaises(IDFError, lambda: sch.pop(1))

    def test_cache_on_filter(self):
        sch = self.idf("Schedule:Compact").filter("name", "System Availability Schedule").one
        self.assertTrue(len(self.idf._.cache) > 0)

        # clear
        self.idf.clear_cache()
        self.assertEqual(0, len(self.idf._.cache))

        # retry
        sch = self.idf("Schedule:Compact").filter("name", "System Availability Schedule").one
        self.assertTrue(len(self.idf._.cache) > 0)


class FourZoneWithShadingSimple1(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    """
    idf = None

    @classmethod
    def tearDownClass(cls):
        del cls.idf

    def test_read_idf(self):
        self.idf = IDF(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf"))


class FiveZoneAirCooled(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    Tested under EPlus 8.1.0 on Mac (Antoine).
    """
    def test_multiple_branch_links(self):
        idf = IDF(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "5ZoneAirCooled.idf"))
        bl = idf("BranchList").filter("Name", "Heating Supply Side Branches").one
        b3 = idf("Branch").filter("Name", "Heating Supply Bypass Branch").one
        self.assertEqual(bl[3], b3)
