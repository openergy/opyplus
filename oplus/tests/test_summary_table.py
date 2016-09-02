import unittest
import os
import tempfile

from oplus import CONF, IDF, simulate


class ZoneWithShadingSimple1(unittest.TestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    """
    idf_path = os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf")
    epw_path = os.path.join(CONF.eplus_base_dir_path, "WeatherData", "USA_CO_Golden-NREL.724666_TMY3.epw")

    def test_summary_table(self):
        with tempfile.TemporaryDirectory() as temp_dir_path:
            idf = IDF(self.idf_path)
            idf.add_object('''OutputControl:Table:Style,Comma,JtoKWH;''')
            idf.add_object('''Output:Table:SummaryReports,AllSummary;''')
            s = simulate(idf, self.epw_path, temp_dir_path)
            self.assertIsNotNone(s.summary_table)  # todo: test
