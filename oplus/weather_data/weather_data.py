import collections
import datetime as dt

import numpy as np
import pandas as pd
from pandas.util.testing import assert_index_equal

from ..util import multi_mode_write, get_mono_line_copyright_message, to_buffer

WEEK_DAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")

# todo: change datetime api (see obat)

# AuxiliaryPrograms, p25, 63
# year is used, but only in E+>=9 if epm option runperiod:treat_weather_as_actual is activated. We consider it
# is mandatory (which is convenient to find start day)
COLUMNS = collections.OrderedDict((  # name: (used, missing)
    ("year", (True, None)),
    ("month", (True, None)),
    ("day", (True, None)),
    ("hour", (True, None)),
    ("minute", (False, None)),
    ("datasource", (False, None)),
    ("drybulb", (True, 99.9)),
    ("dewpoint", (True, 99.9)),
    ("relhum", (True, 999)),
    ("atmos_pressure", (True, 999999)),
    ("exthorrad", (False, 9999)),
    ("extdirrad", (False, 9999)),
    ("horirsky", (True, 9999)),
    ("glohorrad", (False, 9999)),
    ("dirnorrad", (True, 9999)),
    ("difhorrad", (True, 9999)),
    ("glohorillum", (False, 999999)),
    ("dirnorillum", (False, 999999)),
    ("difhorillum", (False, 999999)),
    ("zenlum", (False, 9999)),
    ("winddir", (True, 999)),
    ("windspd", (True, 999)),
    ("totskycvr", (False, 99)),
    ("opaqskycvr", (False, 99)),
    ("visibility", (False, 9999)),
    ("ceiling_hgt", (False, 99999)),
    ("presweathobs", (True, 9)),
    ("presweathcodes", (True, 999999999)),
    ("precip_wtr", (False, 999)),
    ("aerosol_opt_depth", (False, 0.999)),
    ("snowdepth", (True, 999)),
    ("days_last_snow", (False, 99)),
    ("Albedo", (False, 999)),
    ("liq_precip_depth", (True, 999)),
    ("liq_precip_rate", (False, 99)),
))


def to_str(value):
    return "" if value is None else str(value)


class WeatherData:
    def __init__(
            self,
            weather_series,  # dataframe
            latitude,
            longitude,
            timezone_offset,
            elevation,
            city=None,
            state_province_region=None,
            country=None,
            source=None,
            wmo=None,
            design_conditions_source=None,
            design_conditions=None,  # list of design conditions
            typical_extreme_periods=None,  # list of typical/extreme periods
            ground_temperatures=None,  # list of ground temperatures
            leap_year_observed="no",
            daylight_savings_start_day=0,
            daylight_savings_end_day=0,
            holidays=None,  # [(name, day), ...]
            comments_1="",
            comments_2="",
            start_day_of_week=None
    ):
        """
        For more information on following concepts, see EnergyPlus documentation :
            AuxiliaryPrograms.pdf: Weather Converter Program/EnergyPlus Weather File (EPW) Data Dictionary

        Parameters
        ----------
        weather_series: dataframe
            * containing epw columns (some may be missing)
            * missing values may be None or E+ missing value
        latitude
        longitude
        timezone_offset
        elevation
        city
        state_province_region
        country
        source
        wmo
        design_conditions_source
        design_conditions
        typical_extreme_periods
        ground_temperatures
        leap_year_observed
        daylight_savings_start_day
        daylight_savings_end_day
        holidays
        comments_1
        comments_2
        start_day_of_week
        """
        # weather series
        self._weather_series = _sanitize_weather_series(weather_series)

        # start day of week
        if start_day_of_week is None:
            date = dt.date(
                self._weather_series["year"].iloc[0],
                self._weather_series["month"].iloc[0],
                self._weather_series["day"].iloc[0]
            )
            self._start_day_of_week = WEEK_DAYS[date.weekday()]
        else:
            self._start_day_of_week = start_day_of_week

        # headers
        # todo: check headers
        self._headers = dict(
            # mandatory location
            latitude=latitude,
            longitude=longitude,
            timezone_offset=timezone_offset,
            elevation=elevation,
            # optional location
            city=city,
            state_province_region=state_province_region,
            country=country,
            source=source,
            wmo=wmo,
            # design conditions
            design_conditions_source=design_conditions_source,
            design_conditions=[] if design_conditions is None else design_conditions,
            # typical/extreme periods
            typical_extreme_periods=[] if typical_extreme_periods is None else typical_extreme_periods,
            # ground temperatures
            ground_temperatures=[] if ground_temperatures is None else ground_temperatures,
            # holidays/daylight savings
            leap_year_observed=leap_year_observed,
            daylight_savings_start_day=daylight_savings_start_day,
            daylight_savings_end_day=daylight_savings_end_day,
            holidays=[] if holidays is None else holidays,  # [(name, day), ...]
            # comments
            comments_1=comments_1,
            comments_2=comments_2
        )

    def _headers_to_epw(self, use_datetimes=True):
        location = [
            "LOCATION",
            to_str(self._headers["city"]),
            to_str(self._headers["state_province_region"]),
            to_str(self._headers["country"]),
            to_str(self._headers["source"]),
            to_str(self._headers["wmo"]),
            to_str(self._headers["latitude"]),
            to_str(self._headers["longitude"]),
            to_str(self._headers["timezone_offset"]),
            to_str(self._headers["elevation"])
        ]

        # design conditions
        # todo: understand why definition (Auxiliary programs differs from example files (one additionnal comma
        #  in example file USA_FL_Tampa.Intl.AP.722110_TMY3.epw for example, after source)
        design_conditions = [
            "DESIGN CONDITIONS",
            len(self._headers["design_conditions"]),
            self._headers["design_conditions_source"]
        ]
        for dc in self._headers["design_conditions"]:
            design_conditions.extend([dc.name] + dc.values)

        # typical/extreme periods
        typical_extreme_periods = [
            "TYPICAL/EXTREME PERIODS",
            len(self._headers["typical_extreme_periods"])
        ]
        for tep in self._headers["typical_extreme_periods"]:
            typical_extreme_periods.extend([tep.name, tep.period_type, tep.start_day, tep.end_day])

        # ground temperatures
        ground_temperatures = ["GROUND TEMPERATURES", len(self._headers["ground_temperatures"])]
        for gt in self._headers["ground_temperatures"]:
            ground_temperatures.extend(
                [
                    gt.depth,
                    gt.soil_conductivity,
                    gt.soil_density,
                    gt.soil_specific_heat
                ] +
                gt.monthly_average_ground_temperatures
            )

        # holidays/daylight savings
        holidays_daylight_savings = [
            "HOLIDAYS/DAYLIGHT SAVINGS",
            self._headers["leap_year_observed"],
            self._headers["daylight_savings_start_day"],
            self._headers["daylight_savings_end_day"],
            len(self._headers["holidays"])
        ]
        for name, day in self._headers["holidays"]:
            holidays_daylight_savings.extend([name, day])

        # comments
        comments_1 = get_mono_line_copyright_message()
        if (comments_1 not in self._headers["comments_1"]) and (self._headers["comments_1"] != ""):
            comments_1 += " ; " + self._headers["comments_1"]
        comments_1 = ["COMMENTS 1", comments_1]
        comments_2 = ["COMMENTS 2", to_str(self._headers["comments_2"])]

        # data periods
        if use_datetimes and self.has_datetime_instants:
            start_timestamp = self._weather_series.index[0]
            end_timestamp = self._weather_series.index[-1]
            data_periods = [
                "DATA PERIODS",
                1,
                1,
                "",
                WEEK_DAYS[start_timestamp.weekday()],
                f"{start_timestamp.month}/{start_timestamp.day}/{start_timestamp.year}",
                f"{end_timestamp.month}/{end_timestamp.day}/{end_timestamp.year}"
            ]
        else:
            start_month, start_day = self._weather_series["month"].iloc[0], self._weather_series["day"].iloc[0]
            end_month, end_day = self._weather_series["month"].iloc[-1], self._weather_series["day"].iloc[-1]
            data_periods = [
                "DATA PERIODS",
                1,
                1,
                "",
                self._start_day_of_week,
                f"{start_month}/{start_day}",
                f"{end_month}/{end_day}"
            ]

        return "\n".join([",".join([str(cell) for cell in row]) for row in (
            location,
            design_conditions,
            typical_extreme_periods,
            ground_temperatures,
            holidays_daylight_savings,
            comments_1,
            comments_2,
            data_periods
        )]) + "\n"

    # ------------------------------------------------ public api ------------------------------------------------------
    @property
    def has_datetime_instants(self):
        return isinstance(self._weather_series.index, pd.DatetimeIndex)

    def create_datetime_instants(self, start_year=None):
        """
        Parameters
        ----------
        start_year: int or None, default None
            if given, will force year column with start_year (multi-year not supported for now)
        """

        # create and set index
        self._weather_series.index = pd.DatetimeIndex(self._weather_series.apply(
            lambda x: dt.datetime(
                x.year if start_year is None else start_year,
                x.month,
                x.day,
                x.hour-1
            ),
            axis=1
        ))

        # force frequency if needed
        if self._weather_series.index.freq != "H":
            forced_df = self._weather_series.asfreq("H")
            # check no change
            try:
                assert_index_equal(self._weather_series.index, forced_df.index)
            except AssertionError:
                raise ValueError(
                    f"Couldn't convert to hourly datetime instants. Probable cause : "
                    f"given start instant ({self._weather_series.index[0]}) is incorrect and data can't match because "
                    f"of leap year issues."
                ) from None
            # replace old variable
            self._weather_series = forced_df

    def get_weather_series(self):
        """
        Returns
        -------
        weather series dataframe, which contains all the timeseries data. Will be a datetime series or a tuple instants
        series depending on current mode.
        """
        return self._weather_series.copy()

    def get_bounds(self, use_datetimes=True):
        """
        Returns
        -------
        (start, end)

        Datetime instants of beginning and end of data. If no data, will be: (None, None).
        """
        start, end = None, None
        if len(self._weather_series) == 0:
            return start, end

        if use_datetimes and self.has_datetime_instants:
            return self._weather_series.index[0].to_pydatetime(), self._weather_series.index[1].to_pydatetime()

        for i in (0, -1):
            row = self._weather_series.iloc[i, :]
            instant = dt.datetime(row["year"], row["month"], row["day"], row["hour"]-1)

            # store
            if i == 0:
                start = instant
            else:
                end = instant

        return start, end

    def get_info(self):
        start, end = self.get_bounds()
        if start is None:
            start, end = "no data", "no data"

        msg = "WeatherData\n"
        msg += f"\thas datetime instants: {self.has_datetime_instants}\n"
        for k in ("latitude", "longitude", "timezone_offset", "elevation"):
            msg += f"\t{k}: {self._headers[k]}\n"
        msg += f"\tdata period: {start.isoformat()}, {end.isoformat()}"
        return msg

    # ------------------------------------------------- load -----------------------------------------------------------
    @classmethod
    def from_epw(cls, buffer_or_path):
        """
        Parameters
        ----------
        buffer_or_path: buffer or path containing epw format.

        Returns
        -------
        WeatherData instance.
        """
        from .epw_parse import parse_epw
        _, buffer = to_buffer(buffer_or_path)
        with buffer as f:
            return parse_epw(f)

    # ----------------------------------------------- export -----------------------------------------------------------
    def to_epw(self, buffer_or_path=None, use_datetimes=True):
        """
        Parameters
        ----------
        buffer_or_path: buffer or path, default None
            Buffer or path to write into. If None, will return a string containing epw info.
        use_datetimes: bool, default True
            if True and datetime index was created, will use this index to generate epw (start day and data)
            else: will use instant columns information

        Returns
        -------
        None or a string if buffer_or_path is None.
        """
        # copy (will be modified)
        df = self._weather_series.copy()

        # if datetime index, force year
        if use_datetimes and self.has_datetime_instants:
            df["year"] = self._weather_series.index.map(lambda x: x.year)

        # fill nans by default values
        df.fillna(
            value={k: v[1] for k, v in COLUMNS.items() if v[1] is not None},  # pandas does not like None fills
            inplace=True
        )

        # generate content
        epw_content = self._headers_to_epw() + df.to_csv(
            header=False,
            index=False,
            line_terminator="\n"
        )
        
        # write and return
        return multi_mode_write(
            lambda buffer: buffer.write(epw_content),
            lambda: epw_content,
            buffer_or_path=buffer_or_path
        )


def _sanitize_weather_series(df):
    # copy df (we will modify it)
    df = df.copy()

    # check dataframe
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Weather series must be a pandas DataFrame.")

    # create df
    df = pd.DataFrame(collections.OrderedDict((k, df.get(k)) for k in COLUMNS))

    # replace all missing values by nans
    df.replace(
        to_replace={k: v[1] for k, v in COLUMNS.items()},
        value=np.nan,
        inplace=True
    )

    # check that all used columns with no missing value aren't null
    not_null = [k for k, v in COLUMNS.items() if (v[0] and v[1] is None)]
    if df[not_null].isnull().sum().sum() > 0:
        raise ValueError(
            f"given dataframe contains empty values on some mandatory columns:\n{df[not_null].isnull().sum()}"
        )

    # return
    return df
