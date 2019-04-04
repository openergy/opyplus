import collections
import datetime as dt

import pandas as pd
from pandas.util.testing import assert_index_equal

from ..util import multi_mode_write, get_mono_line_copyright_message, to_buffer

WEEK_DAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


INSTANTS_COLUMNS = (
    "year",
    "month",
    "day",
    "hour",
    "minute"
)

WEATHER_SERIES_DEFAULTS = collections.OrderedDict((  # if None: mandatory field, else optional
    ("datasource", ""),
    ("drybulb", None),
    ("dewpoint", None),
    ("relhum", None),
    ("atmos_pressure", None),
    ("exthorrad", 9999),
    ("extdirrad", 9999),
    ("horirsky", 9999),
    ("glohorrad", None),
    ("dirnorrad", None),
    ("difhorrad", None),
    ("glohorillum", 999999),
    ("dirnorillum", 999999),
    ("difhorillum", 999999),
    ("zenlum", 9999),
    ("winddir", None),
    ("windspd", None),
    ("totskycvr", 99),
    ("opaqskycvr", 99),
    ("visibility", 9999),
    ("ceiling_hgt", 99999),
    ("presweathobs", 999),
    ("presweathcodes", 999),
    ("precip_wtr", 999),
    ("aerosol_opt_depth", 999),
    ("snowdepth", 999),
    ("days_last_snow", 99),
    ("Albedo", 999),
    ("liq_precip_depth", 999),
    ("liq_precip_rate", 99)
))

mandatory_columns = tuple(k for k, v in WEATHER_SERIES_DEFAULTS.items() if v is None)  # we use tuple for immutability


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
            design_condition_source=None,
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
            Must at least contain mandatory columns: 'drybulb', 'dewpoint', 'relhum', 'atmos_pressure', 'glohorrad',
            'dirnorrad', 'difhorrad', 'winddir',  'windspd'.

            Two instants modes are available:
             - datetime instants mode: index must be a hourly datetime index
             - tuple mode: index does not matter, and dataframe must have following instants columns: 'year', 'month',
                 'day', 'hour', 'minute'. 'hour' is not written in a epw fashion ([0, 23], not [1, 24] as epw).

            Note that it will be possible, after weather data is created, to switch from datetime to tuple instants (or
            vice versa).
        latitude
        longitude
        timezone_offset
        elevation
        city
        state_province_region
        country
        source
        wmo
        design_condition_source
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
        # instants may be datetimes or tuples
        self._weather_series = _check_and_sanitize_weather_series(weather_series)

        # manage start day of week (only relevant if tuples datetimes)
        self._start_day_of_week = None
        if self.has_tuple_instants and start_day_of_week is not None:
            self._start_day_of_week = start_day_of_week
        else:
            self._set_start_day_of_week()

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
            design_condition_source=design_condition_source,
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

    def _headers_to_epw(self):
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
        design_conditions = ["DESIGN CONDITIONS", len(self._headers["design_conditions"])]
        for dc in self._headers["design_conditions"]:
            design_conditions.extend([dc.name] + dc.values)

        # typical/extreme periods
        typical_extreme_periods = ["TYPICAL/EXTREME PERIODS", len(self._headers["typical_extreme_periods"])
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
        if self.has_datetime_instants:
            start_timestamp = self._weather_series.index[0]
            end_timestamp = self._weather_series.index[-1]
            data_periods = [
                "DATA PERIODS",
                1,
                1,
                WEEK_DAYS[start_timestamp.weekday()],
                f"{start_timestamp.month}/{start_timestamp.day}",
                f"{end_timestamp.month}/{end_timestamp.day}"
            ]
        else:
            start_month, start_day = self._weather_series["month"].iloc[0], self._weather_series["day"].iloc[0]
            end_month, end_day = self._weather_series["month"].iloc[-1], self._weather_series["day"].iloc[-1]
            data_periods = [
                "DATA PERIODS",
                1,
                1,
                self._start_day_of_week,
                f"{start_month}/{start_day}",
                f"{end_month}/{end_day}"
            ]

        return "\n".join([",".join([str(cell) for cell in row]) for row in (
            location,
            design_conditions,
            typical_extreme_periods,
            holidays_daylight_savings,
            comments_1,
            comments_2,
            data_periods
        )]) + "\n"

    def _set_start_day_of_week(self):
        if self.has_datetime_instants:
            date = self._weather_series.index[0]
        else:
            date = dt.date(
                self._weather_series["year"].iloc[0],
                self._weather_series["month"].iloc[0],
                self._weather_series["day"].iloc[0]
            )

        self._start_day_of_week = WEEK_DAYS[date.weekday()]

    # ------------------------------------------------ public api ------------------------------------------------------
    @property
    def has_datetime_instants(self):
        return isinstance(self._weather_series.index, pd.DatetimeIndex)

    @property
    def has_tuple_instants(self):
        return not self.has_datetime_instants

    def switch_to_tuple_instants(self):
        # don't switch if not relevant
        if self.has_tuple_instants:
            return
        # remove datetime index
        self._weather_series.index = range(len(self._weather_series))

    def switch_to_datetime_instants(self):
        # don't switch if not relevant
        if self.has_datetime_instants:
            return

        # create index
        index = pd.DatetimeIndex(self._weather_series.apply(
            lambda x: dt.datetime(x.year, x.month, x.day, x.hour, x.minute),
            axis=1
        ))

        # set new index
        self._weather_series.index = index

        # check and sanitize
        self._weather_series = _check_and_sanitize_datetime_instants(self._weather_series)

        # remove old start day of week
        self._start_day_of_week = None

        # set new start day of week
        self._set_start_day_of_week()

    def get_weather_series(self):
        """
        Returns
        -------
        weather series dataframe, which contains all the timeseries data. Will be a datetime series or a tuple instants
        series depending on current mode.
        """
        return self._weather_series.copy()

    def get_bounds(self):
        """
        Returns
        -------
        (start, end)

        Datetime instants of beginning and end of data. If no data, will be: (None, None).
        """
        start, end = None, None
        if len(self._weather_series) == 0:
            return start, end

        for i in (0, -1):
            # create or find instant
            if self.has_tuple_instants:
                row = self._weather_series.iloc[i, :]
                instant = dt.datetime(row["year"], row["month"], row["day"], row["hour"], row["minute"])
            else:
                instant = self._weather_series.index[i].to_pydatetime()

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
        msg += f"\tinstants: {'tuple' if self.has_tuple_instants else 'datetime'}\n"
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
    def to_epw(self, buffer_or_path=None):
        """
        Parameters
        ----------
        buffer_or_path: buffer or path, default None
            Buffer or path to write into. If None, will return a string containing epw info.

        Returns
        -------
        None or a string if buffer_or_path is None.
        """
        # copy and change hours convention [0, 23] -> [1, 24]
        df = self._weather_series.copy()
        df["hour"] += 1
        epw_content = self._headers_to_epw() + df.to_csv(header=False, index=False)
        return multi_mode_write(
            lambda buffer: buffer.write(epw_content),
            lambda: epw_content,
            buffer_or_path=buffer_or_path
        )


def _check_and_sanitize_weather_series(df):
    # check dataframe
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Weather series must be a pandas DataFrame.")

    # check data columns
    given_columns = set(df.columns)
    diff = set(mandatory_columns).difference(given_columns)
    if len(diff) != 0:
        raise ValueError(f"Missing mandatory columns: {diff}.")

    # prepare data container
    data = collections.OrderedDict()

    # check index info
    is_datetime_index = False
    if isinstance(df.index, pd.DatetimeIndex):  # datetime index mode
        is_datetime_index = True

        # check and sanitize index
        df = _check_and_sanitize_datetime_instants(df)

        # prepare instant columns
        data.update((
            ("year", df.index.year),
            ("month", df.index.month),
            ("day", df.index.day),
            ("hour", df.index.hour),
            ("minute", 0)
        ))

    else:
        # check instant columns
        diff = set(INSTANTS_COLUMNS).difference(given_columns)
        if len(diff) != 0:
            raise ValueError(f"Missing mandatory columns: {diff}.")

        # prepare instant columns
        data.update((k, df[k]) for k in ("year", "month", "day", "hour", "minute"))

    # add data columns
    data.update(collections.OrderedDict(
            (k, df[k] if k in given_columns else v) for k, v in WEATHER_SERIES_DEFAULTS.items())
    )

    # create
    sanitized_df = pd.DataFrame(data, index=df.index if is_datetime_index else None)

    # check no empty values
    nan_columns = set(sanitized_df.columns[sanitized_df.isnull().sum() > 0])
    if len(nan_columns) > 0:
        raise ValueError(f"Some columns contain null values: {tuple(sorted(nan_columns))}")

    # prepare
    return sanitized_df


def _check_and_sanitize_datetime_instants(df):
    """
    Parameters
    ----------
    df

    Returns
    -------
    sanitized df
    """
    # leave if not relevant
    if df is None or len(df) == 0:
        return df

    # check datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("df index must be a datetime index.")

    # force frequency if needed
    if df.index.freq != "H":
        forced_df = df.asfreq("H")
        # check no change
        try:
            assert_index_equal(df.index, forced_df.index)
        except AssertionError:
            raise ValueError(
                f"Couldn't convert to hourly datetime instants. Probable cause : "
                f"given start instant ({df.index[0]}) is incorrect and data can't match because of leap year issues."
            ) from None
        # replace old variable
        df = forced_df

    # check first minute is 0
    if df.index[0].minute != 0:
        raise ValueError("Minutes must be 0.")

    return df
