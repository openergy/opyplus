import unittest
import os
import tempfile

from oplus import Epm, simulate, get_eplus_base_dir_path
from tests.util import iter_eplus_versions


class SummaryTableTest(unittest.TestCase):
    def test_summary_table(self):
        for eplus_version in iter_eplus_versions(self):
            base_dir_path = get_eplus_base_dir_path(eplus_version)
            idf_path = os.path.join(base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf")
            epw_path = os.path.join(base_dir_path, "WeatherData", "USA_CO_Golden-NREL.724666_TMY3.epw")
            with tempfile.TemporaryDirectory() as temp_dir_path:
                idf = Epm.load(idf_path)
                idf.OutputControl_Table_Style.add({0: "Comma", 1: "JtoKWH"})
                idf.Output_Table_SummaryReports.add({0: "AllSummary"})
                s = simulate(idf, epw_path, temp_dir_path)
                self.assertIsNotNone(s.get_out_summary_table())
