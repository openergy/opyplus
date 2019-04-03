import unittest
import os
import tempfile

from oplus import CONF, Epm, simulate


class SummaryTableTest(unittest.TestCase):
    def test_summary_table(self):
        current_eplus_version = CONF.eplus_version
        CONF.eplus_version = (8, 5, 0)
        # todo: check other versions !!!
        try:

            idf_path = os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf")
            epw_path = os.path.join(CONF.eplus_base_dir_path, "WeatherData", "USA_CO_Golden-NREL.724666_TMY3.epw")
            with tempfile.TemporaryDirectory() as temp_dir_path:
                idf = Epm.from_idf(idf_path)
                idf.OutputControl_Table_Style.add({0: "Comma", 1: "JtoKWH"})
                idf.Output_Table_SummaryReports.add({0: "AllSummary"})
                s = simulate(idf, epw_path, temp_dir_path)
                self.assertIsNotNone(s.summary_table)
        finally:
            CONF.eplus_version = current_eplus_version
