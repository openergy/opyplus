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


def parse_output(file_like):
    """
    Only parses hourly (or infra-hourly) data, but does not raise Exception if there is daily or monthly data.
    Reporting frequencies 'Detailed' and 'RunPeriod' not implemented.
    """
    _detailed_ = "Detailed"
    _timestep_ = "TimeStep"
    _hourly_ = "Hourly"
    _daily_ = "Daily"
    _monthly_ = "Monthly"
    _run_period_ = "RunPeriod"

    # ----------------------- LOAD METERS
    # VERSION INFO
    next(file_like)

    # DATA DICTIONARY
    codes_d = {_detailed_: {}, _timestep_: {}, _hourly_: {}, _daily_: {}, _monthly_: {}, _run_period_: {}}
    # {interval:
    #       report_code: [(var_name, var_unit), ...], ...}
    while True:
        # separate content and comment
        line_s = next(file_like)
        line_l = line_s.split("!")
        if len(line_l) == 1:
            content_s, comment = line_l[0], ""
        else:
            content_s, comment = line_l
            comment = comment.strip()
        content_s = content_s.strip()

        if content_s == "End of Data Dictionary":
            break

        # report code
        content_l = content_s.split(",", 2)
        report_code, items_number, vars_l_s = int(content_l[0]), int(content_l[1]), content_l[2]

        # store information if interesting
        if report_code > 5:
            for (interval, pattern) in (
                    (_detailed_, "Each Call"),
                    (_timestep_, _timestep_),
                    (_hourly_, _hourly_),
                    (_daily_, _daily_),
                    (_monthly_, _monthly_),
                    (_run_period_, _run_period_)
            ):
                if pattern in comment:
                    break
            else:
                raise KeyError("Interval not found: '%s'" % line_s)
            codes_d[interval][report_code] = []
            for var_s in vars_l_s.split(",", items_number-1):
                try:
                    var_name, right_s = var_s.split("[")
                    var_unit = right_s[:-1].strip()
                except ValueError:
                    var_name, var_unit = var_s, None
                codes_d[interval][report_code] = (var_name.strip(), var_unit)

    # ------------------------ LOAD DATA
    # constants
    _begin_ = "begin"
    _data_d_ = "data_d"
    _index_l_ = "index_l"
    _dst_l_ = "dst_l"
    _day_types_l_ = "day_types_l"

    # shared local variables
    data_d, index_l, day_types_l, dst_l = None, None, None, None  # dataframe environments
    month_num, day_num, hour_num, end_minute_num, day_type, dst = None, None, None, None, None, None

    # global variables
    raw_envs_l = []

    # loop
    while True:
        line_s = next(file_like).strip()
        if line_s == "End of Data":
            break

        # find item num
        item_num_s, right_s = line_s.split(",", 1)
        item_num = int(item_num_s)

        if item_num > 5:  # value to store
            try:
                val = float(right_s)
            except ValueError:  # happens for 'RunPeriod' or 'Monthly' time step
                val = float(right_s.split(",")[0])  # we don't parse min and max

            # value has been parsed correctly
            try:
                data_d[item_num].append(val)  # data_d belongs to current env
            except (TypeError, KeyError):
                # data_d has not been initialized. Happens for first value of item_num 2, if interval is not known yet
                # find interval
                for interval in (_hourly_, _timestep_, _detailed_):
                    if item_num in codes_d[interval]:
                        break
                else:
                    raise KeyError("Interval not found: '%s'." % line_s)

                # activate item
                data_d = raw_env_d[interval][_data_d_]
                index_l = raw_env_d[interval][_index_l_]
                day_types_l = raw_env_d[interval][_day_types_l_]
                dst_l = raw_env_d[interval][_dst_l_]

                # store
                index_l.append((month_num, day_num, hour_num, end_minute_num))
                day_types_l.append(day_type)
                dst_l.append(dst)

                # append as tried before
                data_d[item_num].append(val)

        elif item_num == 5:  # run period data
            # activate env
            data_d = raw_env_d[_run_period_][_data_d_]
            index_l, day_types_l, dst_l = None, None, None  # not used for run period env

        elif item_num == 2:  # hourly (or timestep) data
            # parse
            # 0-sim_day, 1-month_num, 2-day_num, 3-dst, 4-hour_num, 5-start_minute, 6-end_minute, 7-day_type
            # we don't use start_minute_num
            right_l = right_s.split(",")
            month_num = int(right_l[1])
            day_num = int(right_l[2])
            dst = int(right_l[3])
            hour_num = int(right_l[4])
            end_minute_num = int(float(right_l[6]))
            day_type = right_l[7]

            # deactivate everything (we don't know yet if detailed, hourly or timestep: must wait for first data)
            data_d, index_l, day_types_l, dst_l = None, None, None, None

        elif item_num == 3:  # daily
            # activate env
            data_d = raw_env_d[_daily_][_data_d_]
            index_l = raw_env_d[_daily_][_index_l_]
            dst_l = raw_env_d[_daily_][_dst_l_]
            day_types_l = raw_env_d[_daily_][_day_types_l_]

            # parse
            # 0-sim_day, 1-month_num, 2-day_num, 3-dst, 4-day_type
            right_l = right_s.split(",")
            month_num = int(right_l[1])
            day_num = int(right_l[2])
            dst = int(right_l[3])
            day_type = right_l[4]

            # store
            index_l.append((month_num, day_num))
            day_types_l.append(day_type)
            dst_l.append(dst)

        elif item_num == 4:  # monthly
            # activate env
            data_d = raw_env_d[_monthly_]["data_d"]
            index_l = raw_env_d[_monthly_]["index_l"]
            dst_l, day_types_l = None, None  # not used in monthly environment

            # parse
            # 0-sim_day, 1-month_num
            right_l = right_s.split(",")
            month_num = int(right_l[1])

            # store
            index_l.append(month_num)

        elif item_num == 1:  # new environment
            raw_env_d = {_begin_: line_s}
            for interval in (_detailed_, _timestep_, _hourly_, _daily_, _monthly_, _run_period_):  # meters and index
                if len(codes_d[interval]) == 0:  # no meters
                    continue
                raw_env_d[interval] = dict(data_d=dict([(k, []) for k in codes_d[interval]]), index_l=[])
                if interval == _run_period_:
                    raw_env_d[interval][_index_l_] = ["Total"]
                if interval in (_detailed_, _timestep_, _hourly_, _daily_):  # dst, day type
                    raw_env_d[interval][_dst_l_] = []
                    raw_env_d[interval][_day_types_l_] = []
            raw_envs_l.append(raw_env_d)

    # create environments and store
    envs_d = {}
    if len(raw_envs_l) == 1:
        env_names_l = ["RunPeriod"]
    elif len(raw_envs_l) == 2:
        env_names_l = ["SummerDesignDay", "WinterDesignDay"]
    elif len(raw_envs_l) == 3:
        env_names_l = ["SummerDesignDay", "WinterDesignDay", "RunPeriod"]
    else:
        logger.error("More than three environments were found, unhandled situation. Only first three will be used.")
        env_names_l = ["SummerDesignDay", "WinterDesignDay", "RunPeriod"]
    for env_name, raw_env_d in zip(env_names_l, raw_envs_l[:3]):
        # find env_name
        # for interval in (_detailed_, _timestep_, _hourly_, _daily_):
        #     if not interval in raw_env_d:
        #         continue
        #     first_day_type = raw_env_d[interval][_day_types_l_][0]
        #     env_name = first_day_type if first_day_type in ("SummerDesignDay", "WinterDesignDay") else "RunPeriod"
        #     break
        # else:  # monthly or runperiod
        #     env_name = "RunPeriod"
        #     logger = logging.getLogger(default_logger_name if logger_name is None else logger_name)
        #     logger.error("Did not find env_name for env: '%s'. Env has been skipped." % raw_env_d[_begin_])
        #     continue

        # create and store dataframes
        for interval in (_timestep_, _hourly_, _daily_, _monthly_, _run_period_):
            if interval not in raw_env_d:  # no data
                continue

            # CREATE
            # index
            index_l = raw_env_d[interval][_index_l_]
            if len(index_l) == 0:  # no data
                continue

            if interval in (_detailed_, _timestep_, _hourly_, _daily_):  # multi-index
                names = {
                    _detailed_: ["month", "day", "hour", "minute"],
                    _timestep_: ["month", "day", "hour", "minute"],
                    _hourly_: ["month", "day", "hour", "minute"],
                    _daily_: ["month", "day"]
                }[interval]
                index = pd.MultiIndex.from_tuples(index_l, names=names)
            else:
                index = pd.Index(index_l)

            # dataframe
            data_d = raw_env_d[interval][_data_d_]
            df = pd.DataFrame(data_d, index=index)
            df.rename(columns=dict([(k, codes_d[interval][k][0]) for k in codes_d[interval]]), inplace=True)

            # add dst and day_type if available
            if interval in (_timestep_, _hourly_, _daily_):
                df.insert(0, "dst", raw_env_d[interval]["dst_l"])
                df.insert(0, "day_type", raw_env_d[interval]["day_types_l"])

            # STORE
            if not env_name in envs_d:
                envs_d[env_name] = {}
            if interval in envs_d[env_name]:
                logger.error("Same environment has two identical time steps: '%s'." % raw_env_d[1])
            envs_d[env_name][interval] = df

    return envs_d


def __parse_out_optimized1(file_like):
    """
    Optimization failed...
    Only parses hourly (or infra-hourly) data, but does not raise Exception if there is daily or monthly data.
    Does not transform index into datetime
    """
    # ----------------------- LOAD METERS
    # VERSION INFO
    next(file_like)

    # DATA DICTIONARY
    report_codes_d = {}  # {report_code: [(var_name, var_unit), ...], ...}
    while True:
        line_s = next(file_like).split("!")[0].rstrip()  # we don't take comments and strip the newline character

        if line_s == "End of Data Dictionary":
            break
        line_l = line_s.split(",", 2)

        # report code
        report_code, items_number, vars_l_s = int(line_l[0]), int(line_l[1]), line_l[2]

        if report_code > 5:
            report_codes_d[report_code] = []
            for var_s in vars_l_s.split(",", items_number-1):
                try:
                    var_name, right_s = var_s.split("[")
                    var_unit = right_s[:-1].strip()
                except ValueError:
                    var_name, var_unit = var_s, None
                report_codes_d[report_code] = (var_name.strip(), var_unit)

    # ------------------------ LOAD DATA
    # we only use hourly (or sub-hourly data)
    data = []  # instant_id, timestep_id, meter_i, value
    instant = []  # instant_id, timestep_id, month_num, day_num, hour_num, end_minute_num
    # day_type_id (0 -> simulation, 1 -> SummerDesignDay, 2 -> WinterDesignDay)
    current_instant_id = -1

    day_types_d = {"SummerDesignDay": 1, "WinterDesignDay": 2}  # 0
    for line in file_like:
        line_l = line.split(",", 1)
        try:
            data.append((current_instant_id, int(line_l[0]), float(line_l[1])))
        except ValueError:
            try:
                # line_l: 0-sim_day, 1-month_num, 2-day_num, 3-dst, 4-hour_num, 5-start_minute,
                # 6-end_minute, 7-day_type
                # we don't use sim_day nor start_minute_num
                instant_l = line_l[1].split(",")
                instant.append(
                    (current_instant_id+1,  # instant_id
                     int(instant_l[1]),  # month_num
                     int(instant_l[2]),  # day_num
                     int(instant_l[4]),  # hour_num
                     int(float(instant_l[6])),  # end_minute_num
                     int(line_l[0]),  # timestep_id
                     day_types_d.get(instant_l[7].strip(), 0))  # day_type_id
                    # we didn't use instant_l[0] (sim_day), nor instant_l
                )
                current_instant_id += 1
            except ValueError:
                if int(line_l[0]) != 1:
                    raise Exception("Did not understand line: '%s'." % line)
            except IndexError:
                if line.strip() == 'End of Data':
                    break
    # manage index
    instant_df = pd.DataFrame(instant, columns=["instant_id", "month", "day", "hour", "minute", "timestep_id",
                                                "day_type_id"])
    instant_df["instant_id"] = instant_df.index
    instant_df = instant_df[instant_df["timestep_id"] == 2]
    instant_df = instant_df[instant_df["day_type_id"] == 0]

    instant_df = instant_df.set_index(["month", "day", "hour", "minute"])
    del instant_df["day_type_id"]
    del instant_df["timestep_id"]

    # reshape data and join
    data_df = pd.DataFrame(data, columns=["instant_id", "meter_id", "value"])
    data_df = data_df.pivot(index="instant_id", columns="meter_id", values="value")

    df = instant_df.join(data_df, on="instant_id", how="left")
    del df["instant_id"]
    df.rename(columns=dict([(k, report_codes_d[k][0]) for k in report_codes_d]), inplace=True)

    return df
