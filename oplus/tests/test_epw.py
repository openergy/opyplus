import unittest
import os
import io

from pandas.util.testing import assert_frame_equal

from oplus.configuration import CONF
from oplus.epw import parse_epw, EPW

weather_dir = os.path.join(CONF.eplus_base_dir_path, "WeatherData")
resources_dir = os.path.join(os.path.realpath(os.path.dirname(__file__)), "resources", "epw")


class EPWTestCase(unittest.TestCase):
    def assert_epw_equal(self, expected_content, given_content):
        expected_content_l2 = [[cell.strip() for cell in row.split(",")] for row in expected_content.split("\n")]
        given_content_l2 = [[cell.strip() for cell in row.split(",")] for row in given_content.split("\n")]

        for r, expected_row in enumerate(expected_content_l2):
            for c, expected_cell in enumerate(expected_row):
                try:
                    self.assertEqual(float(expected_cell), float(given_content_l2[r][c]))
                except ValueError:
                    self.assertEqual(expected_cell, given_content_l2[r][c], "Cells differ -> row: %i, column: %i" %
                                     (r, c))


class EPlusWeatherData(EPWTestCase):
    """
    Tested under EPlus 8.1.0 on Windows (Geoffroy).
    """

    def test_epw_to_df_to_epw_integrity(self):
        """
        tests if epw to df to epw works
        """
        epw_files_l = []
        for file_name in os.listdir(weather_dir):
            if os.path.splitext(file_name)[1] == ".epw":
                epw_files_l.append(file_name)

        for file_name in epw_files_l:
            file_path = os.path.join(weather_dir, file_name)
            with open(file_path) as f:
                expected_content = f.read()

            epw = EPW(file_path)
            f = io.StringIO()
            epw.save_as(f, add_copyright=False)

            new_content = f.getvalue()

            self.assert_epw_equal(expected_content, new_content)

    def test_df_get_and_set_integrity(self):
        epw = EPW(os.path.join(weather_dir, "USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw"))
        df = epw.df()
        epw.set_df(df)
        assert_frame_equal(df, epw.df())
