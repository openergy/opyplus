import unittest
import os

from tests.util import iter_eplus_versions

import oplus as op


# schedule_test_record_str = """Schedule:Compact,
#     %s,  !- Name
#     Any Number,              !- Schedule Type Limits Name
#     THROUGH: 12/31,          !- Field 1
#     FOR: AllDays,            !- Field 2
#     UNTIL: 12:00,1,          !- Field 3
#     UNTIL: 24:00,0;          !- Field 5"""

# todo: relink
@unittest.skip("relink")
class DynamicIdfTest(unittest.TestCase):
    """
    The following tests modify the idf.
    """

    @staticmethod
    def get_epm():
        return op.Epm.from_idf(os.path.join(
            op.CONF.eplus_base_dir_path,
            "ExampleFiles",
            "1ZoneEvapCooler.idf")
        )

    def test_idf_add_record(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
            sch_name = "new test schedule"
            idf.add_from_string(schedule_test_record_str % sch_name)
            self.assertEqual(idf.Schedule_Compact.one(lambda x: x.name == sch_name).name, sch_name)

    def test_idf_remove_record(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
            sch_name = "NEW TEST SCHEDULE"
            sch = idf.add_from_string(schedule_test_record_str % sch_name)
            idf.remove(sch)

            # check removed
            self.assertEqual(len(idf.Schedule_Compact.select(lambda x: x.name == sch_name)), 0)

            # check obsolete
            self.assertRaises(ObsoleteRecordError, lambda: print(sch))

    def test_idf_remove_record_raise(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
            zone = idf.Zone.one()
            self.assertRaises(IsPointedError, lambda: idf.remove(zone))

    def test_idf_unlink_and_remove(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
            zone = idf.Zone.one()
            zone.unlink_pointing_records()
            idf.remove(zone)
            self.assertEqual(len(idf.Zone.select()), 0)

    def test_pointing_records(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
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
            idf = self.get_epm()
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
            idf = self.get_epm()
            old_name = "system availability schedule"
            old = idf.Schedule_Compact.one(lambda x: x.name == old_name)
            new = old.copy()
            new_name = old_name + "- new"
            new.name = new_name
            self.assertNotEqual(old, new)

    def test_set_record_simple(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
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
            idf = self.get_epm()

            def set_field():
                idf.building.one().north_axis = "I'm a text, not a real"

            self.assertRaises(ValueError, set_field)

    def test_set_record_broken(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
            supply_fan = idf.Fan_ConstantVolume.one(lambda x: x.name == "supply fan")
            name = supply_fan.availability_schedule_name.name

            def raise_if_you_care():
                supply_fan.availability_schedule_name = schedule_test_record_str % name
            self.assertRaises(BrokenEpmError, raise_if_you_care)

    def test_set_record_broken_constructing_mode(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
            supply_fan = idf.Fan_ConstantVolume.one(lambda x: x.name == "supply fan")
            name = supply_fan.availability_schedule_name.name

            with self.assertRaises(BrokenEpmError):
                with idf.is_under_construction():
                    supply_fan.availability_schedule_name = schedule_test_record_str % name

    def test_extensible(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
            sch = idf.Schedule_Compact.one(lambda x: x.name == "system availability schedule")
            for i in range(1500):
                sch.add_field("12:00")
            self.assertEqual(sch[1300], "12:00")

    def test_pop_end(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
            sch = idf.Schedule_Compact.one(lambda x: x.name == "system availability schedule")
            ini_len = len(sch)
            self.assertEqual("1", sch.pop())
            self.assertEqual(ini_len-1, len(sch))

    def test_pop_middle(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
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
                sch.to_idf())

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
                sch.to_idf())

    def test_pop_raises(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_epm()
            sch = idf.Schedule_Compact.one(lambda x: x.name == "system availability schedule")
            self.assertRaises(RuntimeError, lambda: sch.pop(1))

    def test_cache_on_filter(self):
        for _ in iter_eplus_versions(self):
            # load idf
            idf = self.get_epm()

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
                BrokenEpmError,
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
            with self.assertRaises(BrokenEpmError):
                with idf_manager.is_under_construction:
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
            for pointing_record, pointing_index in zone._._dev_get_pointing_links():
                self.assertEqual(pointing_record._._get_value(pointing_index), None)

            # remove record should be possible
            idf_manager.remove_records(zone)

    def test_set_value_record(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()

            # set
            new_name = "fan availability schedule - 2"
            supply_fan = idf_manager.get_table("Fan:ConstantVolume").one(
                lambda x: x["name"] == "supply fan")
            supply_fan._._set_value("availability schedule name", schedule_test_record_str % new_name)
            print(idf_manager.to_idf())

            # get
            obj = idf_manager.get_table("Fan:ConstantVolume").one(
                lambda x: x["name"] == "supply fan")
            name = obj._._get_value("AvaiLABIlity schedule name")._._get_value("NAME")

            # check
            self.assertEqual(new_name, name)

    def test_set_value_reference(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()

            # set
            new_zone_name = "new zone name"
            zone = idf_manager.get_table("Zone").one()
            pointing_links_l = zone._._dev_get_pointing_links()
            zone._._set_value("name", new_zone_name)

            # check
            self.assertEqual(zone._._get_value("name"), new_zone_name)

            # check pointing
            for pointing_record, pointing_index in pointing_links_l:
                self.assertEqual(pointing_record._.get_serialized_value(pointing_index), new_zone_name)

    def test_copy_record(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()
            zone = idf_manager.get_table("Zone").one()
            new = zone._.copy()
            for i in range(zone._._dev_fields_nb):
                if i == 0:
                    self.assertNotEqual(zone._._get_value(i), new._._get_value(i))
                else:
                    self.assertEqual(zone._._get_value(i), new._._get_value(i))

    def test_replace_values(self):
        for _ in iter_eplus_versions(self):
            idf_manager = self.get_idf_manager()

            # get pointing
            sch = idf_manager.get_table("Schedule:Compact").one(
                lambda x: x["name"] == "heating setpoint schedule")
            pointing_l = [o for (o, i) in sch._._dev_get_pointing_links()]

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
            self.assertEqual([o for (o, i) in sch._._dev_get_pointing_links()], pointing_l)

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

