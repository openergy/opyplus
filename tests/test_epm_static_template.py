import unittest
import os

from tests.util import TESTED_EPLUS_VERSIONS, iter_eplus_versions

from oplus import Epm
from oplus.configuration import CONF


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
            cls.epms_d[eplus_version] = Epm.from_idf(os.path.join(
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

            # check number of pointing tables
            self.assertEqual(4, len(z.get_pointing_records()))

            # check number of pointing objects
            count = 0
            for qs in z.get_pointing_records():

                count += len(qs)
            self.assertEqual(9, count)

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

