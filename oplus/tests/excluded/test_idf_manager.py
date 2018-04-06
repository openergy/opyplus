import unittest
import os

from oplus.idf import BrokenIDFError, IsPointedError, IDF, IDFObject
from oplus.configuration import CONF


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
    idf_manager = None

    @classmethod
    def setUpClass(cls):
        cls.idf_manager = IDF(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))._

    @classmethod
    def tearDownClass(cls):
        del cls.idf_manager

    def test_idf_call(self):
        qs = self.idf_manager.filter_by_ref("Construction")
        self.assertEqual({"R13WALL", "FLOOR", "ROOF31"}, set([c._.get_value("name") for c in qs]))

    def test_qs_one(self):
        self.assertEqual(self.idf_manager.filter_by_ref("BuildingSurface:Detailed"
                            ).filter("naMe", "Zn001:Roof001").one._.get_value("name"), "Zn001:Roof001")

    def test_idf_create_object(self):
        sch_name = "NEW TEST SCHEDULE"
        sch = self.idf_manager.add_object(schedule_test_object_str % sch_name)
        self.assertTrue(isinstance(sch, IDFObject))

    def test_pointing_links_l(self):
        zone = self.idf_manager.filter_by_ref("Zone").one
        d = {  # ref: [pointing_index, nb of objects], ...
            "BuildingSurface:Detailed": [3, 6],  # index 3
            "ZoneInfiltration:DesignFlowRate": [1, 1],  # index 1
            "ZoneHVAC:EquipmentConnections": [0, 1],  # index 0
            "ZoneControl:Thermostat": [1, 1]  # index 1
        }

        # check all pointing
        _d = {}
        for pointing_object, pointing_index in zone._.get_pointing_links_l():
            # check points
            self.assertEqual(pointing_object._.get_value(pointing_index), zone)
            # verify all are identified
            if not pointing_object._.ref in _d:
                _d[pointing_object._.ref] = [pointing_index, 1]
            else:
                self.assertEqual(pointing_index, _d[pointing_object._.ref][0])
                _d[pointing_object._.ref][1] += 1
        self.assertEqual(d, _d)

        # check pointing on pointed_index
        self.assertEqual(len(zone._.get_pointing_links_l(0)), 9)  # 9 pointing
        self.assertEqual(len(zone._.get_pointing_links_l(3)), 0)  # no pointing


class OneZoneEvapCoolerDynamic(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    Here are tests that modify idf.
    """
    idf_manager = None

    @classmethod
    def tearDownClass(cls):
        del cls.idf_manager

    def setUp(self):
        self.idf_manager = IDF(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))._

    def test_idf_add_object(self):
        sch_name = "NEW TEST SCHEDULE"
        new_object = self.idf_manager.add_object(schedule_test_object_str % sch_name)
        self.assertEqual(new_object._.idf_manager, self.idf_manager)

    def test_idf_add_object_broken(self):
        self.assertRaises(BrokenIDFError, lambda: self.idf_manager.add_object("""
        Material,
        C5 - 4 IN HW CONCRETE,   !- Name
        MediumRough,             !- Roughness
        0.1014984,               !- Thickness {m}
        1.729577,                !- Conductivity {W/m-K}
        2242.585,                !- Density {kg/m3}
        836.8000,                !- Specific Heat {J/kg-K}
        0.9000000,               !- Thermal Absorptance
        0.6500000,               !- Solar Absorptance
        0.6500000;               !- Visible Absorptance
        """))

    def test_idf_add_object_broken_construct_mode(self):
        with self.assertRaises(BrokenIDFError):
            with self.idf_manager.under_construction:
                self.idf_manager.add_object("""
                Material,
                C5 - 4 IN HW CONCRETE,   !- Name
                MediumRough,             !- Roughness
                0.1014984,               !- Thickness {m}
                1.729577,                !- Conductivity {W/m-K}
                2242.585,                !- Density {kg/m3}
                836.8000,                !- Specific Heat {J/kg-K}
                0.9000000,               !- Thermal Absorptance
                0.6500000,               !- Solar Absorptance
                0.6500000;               !- Visible Absorptance
                """)

    def test_idf_remove_object(self):
        sch_name = "NEW TEST SCHEDULE"
        sch = self.idf_manager.add_object(schedule_test_object_str % sch_name)
        self.idf_manager.remove_object(sch)
        self.assertEqual(len(self.idf_manager.filter_by_ref("Schedule:Compact").filter("name", sch_name)), 0)

    def test_idf_remove_object_raise(self):
        zone = self.idf_manager.filter_by_ref("Zone").one
        self.assertRaises(IsPointedError, lambda: self.idf_manager.remove_object(zone, raise_if_pointed=True))

    def test_idf_remove_object_no_raise(self):
        zone = self.idf_manager.filter_by_ref("Zone").one
        pointing_links_l = zone._.get_pointing_links_l()
        self.idf_manager.remove_object(zone, raise_if_pointed=False)
        # check that pointing's pointed fields have been removed
        for pointing_object, pointing_index in pointing_links_l:
            self.assertEqual(pointing_object._.get_value(pointing_index), None)

    def test_set_value_object(self):
        new_name = "Fan Availability Schedule - 2"
        supply_fan = self.idf_manager.filter_by_ref("Fan:ConstantVolume").filter("name", "Supply Fan").one
        supply_fan._.set_value("availability schedule name", schedule_test_object_str % new_name)
        # check set
        self.assertEqual(
            self.idf_manager.filter_by_ref("Fan:ConstantVolume").filter(
                "name", "Supply Fan").one._.get_value("AvaiLABIlity schedule name")._.get_value(
                "NAME"), new_name)

    def test_set_value_reference(self):
        new_zone_name = "new zone name"
        zone = self.idf_manager.filter_by_ref("Zone").one
        pointing_links_l = zone._.get_pointing_links_l()
        zone._.set_value("name", new_zone_name)
        # print(zone)
        self.assertEqual(zone._.get_value("name"), new_zone_name)
        for pointing_object, pointing_index in pointing_links_l:
            self.assertEqual(pointing_object._.get_raw_value(pointing_index), new_zone_name)

    def test_copy_object(self):
        zone = self.idf_manager.filter_by_ref("Zone").one
        new = zone._.copy()
        for i in range(zone._.fields_nb):
            if i == 0:
                self.assertNotEqual(zone._.get_value(i), new._.get_value(i))
            else:
                self.assertEqual(zone._.get_value(i), new._.get_value(i))

    def test_replace_values(self):
        sch = self.idf_manager.filter_by_ref("Schedule:Compact").filter("name", "Heating Setpoint Schedule").one
        pointing_l = [o for (o, i) in sch._.get_pointing_links_l()]

        # bigger
        new_str = """Schedule:Compact,
My New Heating Setpoint Schedule,  !- Name
Any Number,              !- Schedule Type Limits Name
Through: 12/31,          !- Field 1
For: AllDays,            !- Field 2
Until: 12:00,20.0,       !- Field 3
Until: 24:00,25.0;       !- Field 3"""
        sch._.replace_values(new_str)

        self.assertEqual(sch["name"], "Heating Setpoint Schedule")
        self.assertEqual([o for (o, i) in sch._.get_pointing_links_l()], pointing_l)

        # smaller
        new_str = """Schedule:Compact,
,  !- Name
Any Number,              !- Schedule Type Limits Name
Through: 12/31,          !- Field 1
For: AllDays,            !- Field 2
Until: 12:00,20.0;       !- Field 3"""

        sch._.replace_values(new_str)
        self.assertEqual(len(sch), 6)
