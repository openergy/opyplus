import unittest
import os

from oplus import BrokenIdfError, IsPointedError, Idf
from oplus.idf.record import Record
from oplus.configuration import CONF
from oplus.tests.util import TESTED_EPLUS_VERSIONS, iter_eplus_versions


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
    idf_managers_d = None

    @classmethod
    def setUpClass(cls):
        cls.idf_managers_d = {}
        for eplus_version in TESTED_EPLUS_VERSIONS:
            CONF.eplus_version = eplus_version
            cls.idf_managers_d[eplus_version] = Idf(os.path.join(
                CONF.eplus_base_dir_path,
                "ExampleFiles",
                "1ZoneEvapCooler.idf")
            )._

    def test_idf_call(self):
        for eplus_version in iter_eplus_versions(self):
            qs = self.idf_managers_d[eplus_version].get_table("Construction").select()
            self.assertEqual({"r13wall", "floor", "roof31"}, set([c._.get_value("name") for c in qs]))

    def test_qs_one(self):
        for eplus_version in iter_eplus_versions(self):
            idf = self.idf_managers_d[eplus_version]
            obj = idf.get_table("BuildingSurface:Detailed").one(
                lambda x: x["naMe"] == "zn001:roof001"
            )
            name = obj._.get_value("name")

            self.assertEqual(
                "zn001:roof001",
                name
            )

    def test_idf_create_record(self):
        for eplus_version in iter_eplus_versions(self):
            sch_name = "NEW TEST SCHEDULE"
            sch = self.idf_managers_d[eplus_version].add_records(schedule_test_record_str % sch_name)
            self.assertTrue(isinstance(sch, Record))

    def test_pointing_links_l(self):
        for eplus_version in iter_eplus_versions(self):
            zone = self.idf_managers_d[eplus_version].get_table("Zone").one()
            d = {  # ref: [pointing_index, nb of records], ...
                "BuildingSurface:Detailed": [3, 6],  # index 3
                "ZoneInfiltration:DesignFlowRate": [1, 1],  # index 1
                "ZoneHVAC:EquipmentConnections": [0, 1],  # index 0
                "ZoneControl:Thermostat": [1, 1]  # index 1
            }
    
            # check all pointing
            _d = {}
            for pointing_record, pointing_index in zone._.get_pointing_links():
                # check points
                self.assertEqual(pointing_record._.get_value(pointing_index), zone)
                # verify all are identified
                if pointing_record._.table.ref not in _d:
                    _d[pointing_record._.table.ref] = [pointing_index, 1]
                else:
                    self.assertEqual(pointing_index, _d[pointing_record._.table.ref][0])
                    _d[pointing_record._.table.ref][1] += 1
            self.assertEqual(d, _d)
    
            # check pointing on pointed_index
            self.assertEqual(len(zone._.get_pointing_links(0)), 9)  # 9 pointing
            self.assertEqual(len(zone._.get_pointing_links(3)), 0)  # no pointing


class DynamicIdfTest(unittest.TestCase):
    """
    The following tests modify the idf.
    """
    @staticmethod
    def get_idf_manager():
        return Idf(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))._

    def test_idf_add_record(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()
            sch_name = "NEW TEST SCHEDULE"
            new_record = idf_manager.add_records(schedule_test_record_str % sch_name)
            self.assertEqual(new_record._.idf_manager, idf_manager)

    def test_idf_add_record_broken(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()
            self.assertRaises(
                BrokenIdfError,
                lambda: idf_manager.add_records("""Material,
    C5 - 4 IN HW CONCRETE,   !- Name
    MediumRough,             !- Roughness
    0.1014984,               !- Thickness {m}
    1.729577,                !- Conductivity {W/m-K}
    2242.585,                !- Density {kg/m3}
    836.8000,                !- Specific Heat {J/kg-K}
    0.9000000,               !- Thermal Absorptance
    0.6500000,               !- Solar Absorptance
    0.6500000;               !- Visible Absorptance""")
                              )

    def test_idf_add_record_broken_construct_mode(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()
            with self.assertRaises(BrokenIdfError):
                with idf_manager.under_construction:
                    idf_manager.add_records("""
                    Material,
                        C5 - 4 IN HW CONCRETE,   !- Name
                        MediumRough,             !- Roughness
                        0.1014984,               !- Thickness {m}
                        1.729577,                !- Conductivity {W/m-K}
                        2242.585,                !- Density {kg/m3}
                        836.8000,                !- Specific Heat {J/kg-K}
                        0.9000000,               !- Thermal Absorptance
                        0.6500000,               !- Solar Absorptance
                        0.6500000;               !- Visible Absorptance""")

    def test_idf_remove_record(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()
            sch_name = "NEW TEST SCHEDULE"
            sch = idf_manager.add_records(schedule_test_record_str % sch_name)
            idf_manager.remove_records(sch)
            self.assertEqual(
                len(idf_manager.get_table("Schedule:Compact").select(lambda x: x["name"] == sch_name)),
                0
            )

    def test_idf_remove_record_raise(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()
            zone = idf_manager.get_table("Zone").one()
            self.assertRaises(IsPointedError, lambda: idf_manager.remove_records(zone))

    def test_idf_unlink_and_remove_record(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()
            zone = idf_manager.get_table("Zone").one()

            # unlink
            zone.unlink_pointing_records()

            # check that pointing's pointed fields have been removed
            for pointing_record, pointing_index in zone._.get_pointing_links():
                self.assertEqual(pointing_record._.get_value(pointing_index), None)

            # remove record should be possible
            idf_manager.remove_records(zone)

    def test_set_value_record(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()

            # set
            new_name = "fan availability schedule - 2"
            supply_fan = idf_manager.get_table("Fan:ConstantVolume").one(
                lambda x: x["name"] == "supply fan")
            supply_fan._.set_value("availability schedule name", schedule_test_record_str % new_name)
            print(idf_manager.to_str())

            # get
            obj = idf_manager.get_table("Fan:ConstantVolume").one(
                lambda x: x["name"] == "supply fan")
            name = obj._.get_value("AvaiLABIlity schedule name")._.get_value("NAME")

            # check
            self.assertEqual(new_name, name)

    def test_set_value_reference(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()

            # set
            new_zone_name = "new zone name"
            zone = idf_manager.get_table("Zone").one()
            pointing_links_l = zone._.get_pointing_links()
            zone._.set_value("name", new_zone_name)

            # check
            self.assertEqual(zone._.get_value("name"), new_zone_name)

            # check pointing
            for pointing_record, pointing_index in pointing_links_l:
                self.assertEqual(pointing_record._.get_raw_value(pointing_index), new_zone_name)

    def test_copy_record(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()
            zone = idf_manager.get_table("Zone").one()
            new = zone._.copy()
            for i in range(zone._.fields_nb):
                if i == 0:
                    self.assertNotEqual(zone._.get_value(i), new._.get_value(i))
                else:
                    self.assertEqual(zone._.get_value(i), new._.get_value(i))

    def test_replace_values(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()

            # get pointing
            sch = idf_manager.get_table("Schedule:Compact").one(
                lambda x: x["name"] == "heating setpoint schedule")
            pointing_l = [o for (o, i) in sch._.get_pointing_links()]

            # replace with bigger
            new_str = """
            Schedule:Compact,
                My New Heating Setpoint Schedule,  !- Name
                Any Number,              !- Schedule Type Limits Name
                Through: 12/31,          !- Field 1
                For: AllDays,            !- Field 2
                Until: 12:00,20.0,       !- Field 3
                Until: 24:00,25.0;       !- Field 3"""
            sch._.replace_values(new_str)

            # check
            self.assertEqual(sch["name"], "heating setpoint schedule")
            self.assertEqual([o for (o, i) in sch._.get_pointing_links()], pointing_l)

            # replace with smaller
            new_str = """
            Schedule:Compact,
                ,  !- Name
                Any Number,              !- Schedule Type Limits Name
                Through: 12/31,          !- Field 1
                For: AllDays,            !- Field 2
                Until: 12:00,20.0;       !- Field 3"""
            sch._.replace_values(new_str)

            # check
            self.assertEqual(len(sch), 6)
