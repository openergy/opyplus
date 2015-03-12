import unittest
import os

from oplus.idf import IDF, IDFObject
from oplus.idf import BrokenIDFError, IsPointedError
from oplus.configuration import CONFIG


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
    @classmethod
    def setUpClass(cls):
        cls.idf = IDF(os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))

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


class OneZoneEvapCoolerDynamic(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    Here are tests that modify idf.
    """
    def setUp(self):
        self.idf = IDF(os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))

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


class FourZoneWithShadingSimple1(unittest.TestCase):
    def test_read_idf(self):
        self.idf = IDF(os.path.join(CONFIG.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf"))