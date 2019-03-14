import unittest
import os

from tests.util import TESTED_EPLUS_VERSIONS, iter_eplus_versions

from oplus import Epm, BrokenEpmError, IsPointedError
from oplus.epm.record import Record
from oplus.configuration import CONF
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
    epms_d = None

    @classmethod
    def setUpClass(cls):
        cls.epms_d = {}

        for eplus_version in TESTED_EPLUS_VERSIONS:
            CONF.eplus_version = eplus_version
            cls.epms_d[eplus_version] = Epm(os.path.join(
                CONF.eplus_base_dir_path,
                "ExampleFiles",
                "1ZoneEvapCooler.idf")
            )

    @classmethod
    def tearDownClass(cls):
        del cls.epms_d
        
    # ----------------------------------------- navigate ---------------------------------------------------------------
    def test_table_getattr(self):
        for eplus_version in iter_eplus_versions(self):
            ref = "BuildingSurface_Detailed"

            # exact ref
            bsd = self.epms_d[eplus_version].BuildingSurface_Detailed
            self.assertEqual(bsd.get_ref(), ref)

            # case insensitive ref
            bsd = self.epms_d[eplus_version].BuILdINGsURFaCE_DETaILED
            self.assertEqual(bsd.get_ref(), ref)

    def test_record_getitem_getattr_and_pk(self):
        bsd_name = "zn001:roof001"
        for eplus_version in iter_eplus_versions(self):
            bsd = self.epms_d[eplus_version].BuildingSurface_Detailed[bsd_name]
            self.assertEqual(bsd.name, bsd_name)
            self.assertEqual(bsd[0], bsd_name)
            self.assertEqual(bsd.get_pk(), bsd_name)

    def test_get_table(self):
        for eplus_version in iter_eplus_versions(self):
            table = self.epms_d[eplus_version].Construction
            self.assertEqual(
                {"r13wall", "floor", "roof31"},
                set([c.name for c in table.select()])
            )

    def test_qs_one(self):
        for eplus_version in iter_eplus_versions(self):
            self.assertEqual(
                self.epms_d[eplus_version].BuildingSurface_Detailed.one(
                    lambda x: x.name == "zn001:roof001").name,
                "zn001:roof001"
            )

    def test_qs_select(self):
        for eplus_version in iter_eplus_versions(self):
            epm = self.epms_d[eplus_version]
            # get all building surfaces that have a zone with Z-Origin 0
            simple_filter_l = [bsd for bsd in epm.BuildingSurface_Detailed if bsd.zone_name[4] == 0]

            multi_filter_l = list(
                epm.BuildingSurface_Detailed.select(
                    lambda x: x.zone_name[4] == 0
                )
            )
            self.assertEqual(simple_filter_l, multi_filter_l)

    def test_pointing(self):
        for eplus_version in iter_eplus_versions(self):
            epm = self.epms_d[eplus_version]
            z = epm.zone.one()

            # check pointing surfaces
            self.assertEqual({
                "zn001:wall001",
                "zn001:wall002",
                "zn001:wall003",
                "zn001:wall004",
                "zn001:flr001",
                "zn001:roof001",
            },
                {s.name for s in z.get_pointing_records().BuildingSurface_Detailed}
            )

            # check number of pointing objects
            self.assertEqual(9, len(z.get_pointing_records()))

    def test_pointed(self):
        for eplus_version in iter_eplus_versions(self):
            epm = self.epms_d[eplus_version]
            bsd = epm.BuildingSurface_Detailed["zn001:wall001"]

            pointed = bsd.get_pointed_records()

            self.assertEqual(2, len(pointed))

            self.assertEqual("main zone", pointed.Zone.one().name)
            self.assertEqual("r13wall", pointed.Construction.one().get_pk())

    # ----------------------------------------- construct --------------------------------------------------------------
    def test_add_records(self):
        for eplus_version in iter_eplus_versions(self):
            epm = self.epms_d[eplus_version]
            schedule_compact = epm.Schedule_Compact

            # add schedule with simple field
            sch1 = schedule_compact.add(name="sch1")
            self.assertEqual(sch1.name, "sch1")

            # add schedule with extensible fields
            sch2 = schedule_compact.add(  # kwargs like
                name="sch2",
                field_1="Through: 12/31",
                field_2="For: AllDays",
                field_3="Until: 24:00,4"
            )
            self.assertEqual(5, len(sch2))

            # add schedule from dict
            sch3 = schedule_compact.add({  # dict like
                0: "sch3",
                2: "Through: 12/31",
                "field_2": "For: AllDays",
                "field_3": "Until: 24:00,4"
            })
            self.assertEqual(5, len(sch3))

            # batch add schedules
            schedules = schedule_compact.batch_add([
                dict(name="batch0"),
                dict(name="batch1"),
                dict(name="batch2")
            ])
            self.assertEqual(3, len(schedules))
            self.assertEqual(set(schedules), set(schedule_compact.select(lambda x: "batch" in x.name)))

    # todo: test pk change
    # todo: test link/hook change
    # todo: test extensible fields limitations
    # todo: check to_str, including comments and copyright
    # todo: check __dir__ and help
    # todo: shouldn't we propose a record.delete() method ? (and queryset.delete()) ?


class DynamicIdfTest(unittest.TestCase):
    """
    The following tests modify the idf.
    """

    @staticmethod
    def get_idf():
        return Epm(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))

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
            self.assertRaises(BrokenEpmError, raise_if_you_care)

    def test_set_record_broken_constructing_mode(self):
        for _ in iter_eplus_versions(self):
            idf = self.get_idf()
            supply_fan = idf.Fan_ConstantVolume.one(lambda x: x.name == "supply fan")
            name = supply_fan.availability_schedule_name.name

            with self.assertRaises(BrokenEpmError):
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
                self.assertEqual(pointing_record._.get_raw_value(pointing_index), new_zone_name)

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


class MiscellaneousIdfTest(unittest.TestCase):
    def test_simple_read(self):
        for _ in iter_eplus_versions(self):
            for idf_name in ("4ZoneWithShading_Simple_1",):
                Epm(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", f"{idf_name}.idf"))

    def test_multiple_branch_links(self):
        for _ in iter_eplus_versions(self):
            idf = Epm(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "5ZoneAirCooled.idf"))
            bl = idf.BranchList.one(lambda x: x.name == "heating supply side branches")
            b3 = idf.Branch.one(lambda x: x.name == "heating supply bypass branch")
            self.assertEqual(bl[3], b3)
