import unittest
import os
import tempfile

from oplus import CONF, Idf, simulate


class SummaryTableTest(unittest.TestCase):
    idf_path = os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf")
    epw_path = os.path.join(CONF.eplus_base_dir_path, "WeatherData", "USA_CO_Golden-NREL.724666_TMY3.epw")

    def test_summary_table(self):
        with tempfile.TemporaryDirectory() as temp_dir_path:
            idf = Idf(self.idf_path)
            idf.add('''OutputControl:Table:Style,Comma,JtoKWH;''')
            idf.add('''Output:Table:SummaryReports,AllSummary;''')
            s = simulate(idf, self.epw_path, temp_dir_path)
            self.assertIsNotNone(s.summary_table)
