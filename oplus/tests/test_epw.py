import unittest
import os
import io

from oplus.configuration import CONF
from oplus.epw import Epw
from oplus.tests.util import assert_epw_equal, iter_eplus_versions

from pandas.util.testing import assert_frame_equal


class EPlusWeatherData(unittest.TestCase):
    def test_epw_to_df_to_epw_integrity(self):
        """
        tests if epw to df to epw works
        """
        for _ in iter_eplus_versions(self):
            weather_dir = os.path.join(CONF.eplus_base_dir_path, "WeatherData")

            # check Chicago
            file_path = os.path.join(weather_dir, "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw")
            with open(file_path) as f:
                expected_content = f.read()

            # read
            epw = Epw(file_path)

            # write
            f = io.StringIO()
            epw.save_as(f, add_copyright=False)
            new_content = f.getvalue()

            # check
            assert_epw_equal(expected_content, new_content)

    def test_df_get_and_set_integrity(self):
        for _ in iter_eplus_versions(self):
            weather_dir = os.path.join(CONF.eplus_base_dir_path, "WeatherData")

            # check sf
            epw = Epw(os.path.join(weather_dir, "USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw"))

            # read
            df = epw.df()

            # write
            epw.set_df(df)

            # check
            assert_frame_equal(df, epw.df())
