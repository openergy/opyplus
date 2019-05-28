import unittest
import os

import pandas as pd

from oplus.configuration import CONF
from oplus import WeatherData
from oplus.compatibility import get_eplus_base_dir_path
from tests.util import assert_epw_equal, iter_eplus_versions

from pandas.util.testing import assert_frame_equal


class EPlusWeatherData(unittest.TestCase):
    # todo: make better checks
    def test_weather_series(self):
        for eplus_version in iter_eplus_versions(self):
            weather_dir = os.path.join(get_eplus_base_dir_path(eplus_version), "WeatherData")

            # check Chicago
            file_path = os.path.join(weather_dir, "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw")

            # get weather series csv
            with open(file_path) as f:
                # skip header
                for i in range(8):
                    next(f)
                expected_df = pd.read_csv(f, header=None)

            # create weather data
            weather_data = WeatherData.from_epw(file_path)
            generated_df = weather_data.get_weather_series()
            generated_df.columns = range(len(generated_df.columns))  # remove columns (for comparison)

            # check
            # correct year convention
            expected_df[3] -= 1
            assert_frame_equal(expected_df, generated_df)


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
