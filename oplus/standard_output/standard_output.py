"""
Standard Output File
------------------------

"""
import datetime as dt
import logging
import os

import pandas as pd

from oplus.configuration import CONF
from oplus.util import EPlusDt, get_start_dt


logger = logging.getLogger(__name__)


class StandardOutputFile:
    DETAILED = "Detailed"
    TIME_STEP = "TimeStep"
    HOURLY = "Hourly"
    DAILY = "Daily"
    MONTHLY = "Monthly"
    RUN_PERIOD = "RunPeriod"  # !! is used as a time_step and a Environment

    SUMMER_DESIGN_DAY = "SummerDesignDay"
    WINTER_DESIGN_DAY = "WinterDesignDay"

    ENVIRONMENTS = (RUN_PERIOD, SUMMER_DESIGN_DAY, WINTER_DESIGN_DAY)
    TIME_STEPS = (DETAILED, TIME_STEP, HOURLY, DAILY, MONTHLY, RUN_PERIOD)

    def __init__(self, path, encoding=None, start=None):
        assert os.path.exists(path), "No file at given path: '%s'." % path
        self._path = path
        self._encoding = encoding

        self._start_dt = None if start is None else get_start_dt(start)

        # {run_period: {hourly: df, daily: df, monthly: df}, summer_design: df, winter_design: df}
        # datetime indexes are not managed here
        self._envs_d = self._parse()

    def set_start(self, start):
        self._start_dt = get_start_dt(start)

    def _parse(self):
        with open(self._path, "r", encoding=CONF.encoding if self._encoding is None else self._encoding) as f:
            return parse_output(f)

    def df(self, environment=None, time_step=None, start=None, datetime_index=None):
        # todo: start does not always work. Do datetime work well ? Do EPlusDt work well ?
        """
        environment: 'RunPeriod', 'SummerDesignDay', 'WinterDesignDay' (default: first available)
        time_step: 'Detailed', 'TimeStep', 'Hourly', 'Daily', 'Monthly', 'RunPeriod' (default: first available)
        datetime_index: if None: True if possible, else False
        start: explain mechanism (can have been set with 'set_start' or while initialization)
        """
        # ------------------------------------ manage arguments --------------------------------------------------------
        # ENVIRONMENT
        # set environment if needed
        if environment is None:
            for environment in self.ENVIRONMENTS:
                if environment in self._envs_d:
                    break

        # check if environment is ok
        assert environment in self.ENVIRONMENTS, "Unknown environment: '%s'." % environment

        # check availability
        if environment not in self._envs_d:  # no available environment
            return None

        # set environment
        env_d = self._envs_d[environment]

        # TIME STEP
        # set time step if needed
        if time_step is None:
            for time_step in self.TIME_STEPS:
                if time_step in env_d:
                    break

        # check if time step is ok
        assert time_step in self.TIME_STEPS, \
            "Unknown time_step: '%s' (must be: %s)." % (time_step, ", ".join(self.TIME_STEPS))

        # check availability
        if time_step not in env_d:  # no available time step
            return None

        # start_dt
        start_dt = self._start_dt if start is None else get_start_dt(start)

        # datetime_index
        if datetime_index is None:
            datetime_index = start_dt is not None
        if (datetime_index is True) and (start_dt is None):
            raise ValueError(
                "datetime_index mode can only be used if you indicated start. Use tuple index mode or "
                "registered start (set_start, on initialization of Output object or as df method argument."
            )

        # ------------------------------------ manage data frame -------------------------------------------------------
        # fetch dataframe
        if not time_step in env_d:
            return None
        df = env_d[time_step]

        # return if no conversion needed
        if not datetime_index or (time_step == self.RUN_PERIOD):
            return df

        # convert if needed
        start_esodt = EPlusDt.from_datetime(start_dt)

        if time_step in (self.DETAILED, self.TIME_STEP, self.HOURLY):
            row_to_esodt = lambda row: EPlusDt(*row[:4])
        elif time_step == self.DAILY:
            row_to_esodt = lambda row: EPlusDt(*(row[:2] + (1, 0)))
        else:  # monthly (RunPeriod has been returned)
            row_to_esodt = lambda row: EPlusDt(row, 1, 1, 0)

        start_standard_dt = start_esodt.standard_dt

        def row_to_dt(row):
            esodt = row_to_esodt(row)
            _year = start_dt.year + 1 if esodt.standard_dt <= start_standard_dt else start_dt.year
            return esodt.datetime(_year)

        df = df.copy()
        df.index = df.index.map(row_to_dt)
        df.sort_index(inplace=True)
        freq = None
        if time_step in (self.TIME_STEP, self.DETAILED):
            for year, year_df in df.groupby(lambda x: x.year):
                freq = year_df.index.inferred_freq
                if freq is not None:
                    break
            else:
                logger.warning("Could not find freq for sub-hourly data (not enough values). Did not reindex.")
                return df
        elif time_step == self.HOURLY:
            freq = "H"
        elif time_step == self.DAILY:
            freq = "D"
        elif time_step == self.MONTHLY:
            freq = "MS"

        # check that everything is ok while reindex
        before_nb = len(df)
        # todo: reindex will not work if a schedule is associated
        df = df.reindex(index=pd.date_range(df.index[0], df.index[-1], freq=freq))
        null_nb = (df.notnull().sum(axis=1) == 0).sum()
        if len(df) != before_nb + null_nb:
            logger.error(
                "BUG: Some values were lost during reindex (before reindex: %i, after: %i (%i full, %i empty)."
                % (before_nb, len(df), len(df)-null_nb, null_nb))

        return df

    def info(self):
        msg = ""
        for simulation_period in self._envs_d:
            msg += "\n\t%s: %s" % (simulation_period, ", ".join(self._envs_d[simulation_period].keys()))
        if msg == "":
            msg = "No data available."
        else:
            msg = "Available data:" + msg
        return msg

    @property
    def environments(self):
        return self._envs_d.keys()



