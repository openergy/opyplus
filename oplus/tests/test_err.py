import unittest
import os
import tempfile


from oplus import CONF, IDF, simulate



class ZoneWithShadingSimple1(unittest.TestCase):
    idf_path = os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "4ZoneWithShading_Simple_1.idf")
    epw_path = os.path.join(CONF.eplus_base_dir_path, "WeatherData", "USA_CO_Golden-NREL.724666_TMY3.epw")

    def test_err(self):
        with tempfile.TemporaryDirectory() as temp_dir_path:
            idf = IDF(self.idf_path)
            idf.add_object('''OutputControl:Table:Style,Comma,JtoKWH;''')
            idf.add_object('''Output:Table:SummaryReports,AllSummary;''')
            s = simulate(idf, self.epw_path, temp_dir_path)
            self.assertIsNotNone(s.err)  # todo: test results !!
