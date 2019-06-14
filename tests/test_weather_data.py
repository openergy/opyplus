import tempfile
import unittest
import os
import io

import pandas as pd

from oplus.configuration import CONF
from oplus import WeatherData
from oplus.compatibility import get_eplus_base_dir_path
from tests.util import assert_epw_equal, iter_eplus_versions  # todo: improve epw-equal and use it

from pandas.util.testing import assert_frame_equal


class EPlusWeatherData(unittest.TestCase):
    # todo: make better checks
    def test_weather_series(self):

        for eplus_version in iter_eplus_versions(self):
            weather_dir = os.path.join(get_eplus_base_dir_path(eplus_version), "WeatherData")

            # check Chicago
            file_path = os.path.join(weather_dir, "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw")

            # create weather data
            weather_data0 = WeatherData.load(file_path)

            # create new epw
            epw1 = weather_data0.save()
            weather_data1 = WeatherData.load(io.StringIO(epw1))

            # check
            assert_frame_equal(
                weather_data0.get_weather_series(),
                weather_data1.get_weather_series()
            )

    # todo: test extensively (including headers)

    # def test_df_get_and_set_integrity(self):
    #     for _ in iter_eplus_versions(self):
    #         weather_dir = os.path.join(CONF.eplus_base_dir_path, "WeatherData")
    #
    #         # check sf
    #         epw = Epw(os.path.join(weather_dir, "USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw"))
    #
    #         # read
    #         df = epw.df()
    #
    #         # write
    #         epw.set_df(df)
    #
    #         # check
    #         assert_frame_equal(df, epw.df())
