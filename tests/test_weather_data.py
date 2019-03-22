import unittest
import os
import io

from oplus.configuration import CONF
from oplus import WeatherData
from tests.util import assert_epw_equal, iter_eplus_versions

from pandas.util.testing import assert_frame_equal


class EPlusWeatherData(unittest.TestCase):
    def test_df_integrity(self):
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
            weather_data = WeatherData.from_epw(file_path)

            # write
            generated_content = weather_data.to_epw()

            # check
            # todo

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
