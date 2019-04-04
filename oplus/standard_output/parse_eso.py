from collections import namedtuple, OrderedDict
import re

import pandas as pd

VariableInfo = namedtuple("VariableInfo", ("code", "key_value", "name", "unit", "frequency", "info"))

Environment = namedtuple("Environment", ("title", "latitude", "longitude", "timezone_offset", "elevation"))


comment_brackets_pattern = re.compile(r"\s\[[\w,]+\]")

# frequencies
TIMESTEP = "timestep"
HOURLY = "hourly"
DAILY = "daily"
MONTHLY = "monthly"
ANNUAL = "annual"
RUN_PERIOD = "run_period"

FREQUENCIES = TIMESTEP, HOURLY, DAILY, MONTHLY, ANNUAL, RUN_PERIOD

# constants
EACH_CALL = "each call"

# instant codes

# timestep
_timestep_month_ = "timestep_month"
_timestep_day_ = "timestep_day"
_timestep_hour_ = "timestep_hour"
_timestep_minute_ = "timestep_minute"
_timestep_dst_ = "timestep_dst"
_timestep_day_type_ = "timestep_day_type"
# hourly instants
_hourly_month_ = "hourly_month"
_hourly_day_ = "hourly_day"
_hourly_hour_ = "hourly_hour"
_hourly_minute_ = "hourly_minute"
_hourly_dst_ = "hourly_dst"
_hourly_day_type_ = "hourly_day_type"
# daily instants
_daily_month_ = "daily_month"
_daily_day_ = "daily_day"
_daily_dst_ = "daily_dst"
_daily_day_type_ = "daily_day_type"
# monthly instants
_monthly_month_ = "monthly_month"
# annual instants
_annual_year_ = "annual_year"


# other
METER = "Meter"


def parse(file_like):
    # ----------------------- LOAD METERS
    # VERSION
    row_l = next(file_like).split(",")
    match = re.fullmatch(r"\s*Version\s*(\d+.\d+.\d+)-([\w\d]+)\s*", row_l[2])
    detailed_version = tuple(int(s) for s in match.group(1).split(".")) + (match.group(2),)

    # for eplus >= 9, code 6 is for annual variables (did not exist before)
    annual_code = None if detailed_version[0] < 9 else "6"
    max_data_dict_info_code_int = 5 if annual_code is None else int(annual_code)
    manage_timesteps = False

    # DATA DICTIONARY
    variables_info = OrderedDict()  # {code: Variable, ....

    while True:
        row = next(file_like).strip()

        # leave if finished
        if row == "End of Data Dictionary":
            break

        # get code and vars_num
        code, vars_num, other = row.split(",", 2)  # we use str codes, for optimization (avoids conversion)
        vars_num = int(vars_num)

        # continue if concerns dictionary info (is always the same and is documented, no need to parse)
        if int(code) <= max_data_dict_info_code_int:
            continue

        # split content and comment
        content, comment = other.split(" !")

        # parse content
        try:
            key_value, var_name = content.split(",")
            key_value = key_value.lower()  # no retaincase
            var_name, unit = var_name.split(" [")
            unit = unit[:-1]
        except ValueError:  # may only have one element (for example Custom:Meter)
            key_value = content
            var_name = METER
            key_value, unit = key_value.split(" [")
            unit = unit[:-1]
            key_value = key_value.lower()  # no retaincase

        # parse comment
        if vars_num != 1:  # remove brackets if relevant
            comment = re.sub(comment_brackets_pattern, "", comment)
        timestep_and_or_info = comment.split(" ,")

        # frequency
        frequency = timestep_and_or_info[0].lower()  # no retaincase
        if frequency in (EACH_CALL, TIMESTEP):  # depends on eplus version (8.5.0: timestep, 9.0.1: each call)
            frequency = TIMESTEP
            manage_timesteps = True
        elif frequency == "runperiod":
            frequency = RUN_PERIOD  # we add underscore

        # info
        try:
            info = timestep_and_or_info[1]
        except IndexError:
            info = ""

        # store variable info
        variables_info[code] = VariableInfo(
            code,
            key_value,
            var_name,
            unit,
            frequency,
            info
        )

    # ------------------------ LOAD DATA
    # global variables
    environments = OrderedDict()  # {environment_name: environment: ,
    environments_data = {}  # {environment_name: data, ...

    # current variables
    current_data = None
    last_timestep_end = None  # (month, day, hour, end_minute) (necessary info to distinguish hourly from timestamp)

    # loop
    while True:
        row = next(file_like).strip()

        # leave if finished
        if row == "End of Data":
            break

        # find item num
        code, other = row.split(",", 1)

        if code == "1":  # new environment
            other = other.split(",")

            # create and store environment
            env = Environment(
                other[0].lower(),
                float(other[1]),
                float(other[2]),
                float(other[3]),
                float(other[4])
            )
            environments[env.title] = env

            # prepare and store environment data
            # data: { code: values, ...
            current_data = dict((k, []) for k in (
                    ((  # timestep instants (if relevant)
                         _timestep_month_,
                         _timestep_day_,
                         _timestep_hour_,
                         _timestep_minute_,
                         _timestep_dst_,
                         _timestep_day_type_
                     ) if manage_timesteps else ()) +
                    (
                        # hourly instants
                        _hourly_month_,
                        _hourly_day_,
                        _hourly_hour_,
                        _hourly_minute_,
                        _hourly_dst_,
                        _hourly_day_type_,
                        # daily instants
                        _daily_month_,
                        _daily_day_,
                        _daily_dst_,
                        _daily_day_type_,
                        # monthly instants
                        _monthly_month_,
                        # annual instants
                        _annual_year_
                    ) +
                    tuple(variables_info)))
            environments_data[env.title] = current_data

        elif code == "2":  # timestep (and hourly) data
            # 0-sim_day, 1-month_num, 2-day_num, 3-dst, 4-hour_num, 5-start_minute, 6-end_minute, 7-day_type
            other = other.split(",")

            if manage_timesteps:
                month = int(other[1])
                day = int(other[2])
                hour = int(other[4])-1
                minute = int(float(other[5]))
                end_minute = int(float(other[6]))
                dst = int(other[3])
                day_type = other[7]
                if last_timestep_end == (month, day, hour, end_minute):  # hourly instant
                    current_data[_hourly_month_].append(month)
                    current_data[_hourly_day_].append(day)
                    current_data[_hourly_hour_].append(hour)
                    current_data[_hourly_dst_].append(dst)
                    current_data[_hourly_day_type_].append(day_type)
                else:  # timestep instant
                    current_data[_timestep_month_].append(month)
                    current_data[_timestep_day_].append(day)
                    current_data[_timestep_hour_].append(hour)
                    current_data[_timestep_minute_].append(minute)
                    current_data[_timestep_dst_].append(dst)
                    current_data[_timestep_day_type_].append(day_type)

                    last_timestep_end = (month, day, hour, end_minute)
            else:
                # only store hour instant
                current_data[_hourly_month_].append(int(other[1]))
                current_data[_hourly_day_].append(int(other[2]))
                current_data[_hourly_hour_].append(int(other[4])-1)
                current_data[_hourly_dst_].append(int(other[3]))
                current_data[_hourly_day_type_].append(other[7])

        elif code == "3":  # daily
            # 0-sim_day, 1-month_num, 2-day_num, 3-dst, 4-day_type
            other = other.split(",")
            current_data[_daily_month_].append(int(other[1]))
            current_data[_daily_day_].append(int(other[2]))
            current_data[_daily_day_type_].append(int(other[3]))
            current_data[_daily_dst_].append(other[4])

        elif code == "4":  # monthly
            other = other.split(",")
            current_data[_monthly_month_].append(int(other[1]))

        elif code == "5":  # run period data
            # nothing to do
            pass

        elif code == annual_code:  # will only be used for >= 9.0.1
            current_data[_annual_year_].append(int(other))

        else:  # value to store
            # parse
            try:
                val = float(other)
            except ValueError:  # happens for 'RunPeriod' or 'Monthly' time step
                val = float(other.split(",")[0])  # we don't parse min and max

            # store
            current_data[code].append(val)

    # prepare data frames container and codes
    environments_dfs = dict((env_title, {}) for env_title in environments)  # {environment_title: {frequency: df, ...
    timestep_codes = tuple(sorted(var.code for var in variables_info.values() if var.frequency == TIMESTEP))
    hourly_codes = tuple(sorted(var.code for var in variables_info.values() if var.frequency == HOURLY))
    daily_codes = tuple(sorted(var.code for var in variables_info.values() if var.frequency == DAILY))
    monthly_codes = tuple(sorted(var.code for var in variables_info.values() if var.frequency == MONTHLY))
    annual_codes = tuple(sorted(var.code for var in variables_info.values() if var.frequency == ANNUAL))
    run_period_codes = tuple(sorted(var.code for var in variables_info.values() if var.frequency == RUN_PERIOD))
    columns_rename = dict((var.code, f"{var.key_value.lower()},{var.name}") for var in variables_info.values())

    # create dataframes
    for env_title, env_data in environments_data.items():
        # create dataframes dict and store
        env_dfs = dict((frequency, None) for frequency in (TIMESTEP, HOURLY, DAILY, MONTHLY, ANNUAL, RUN_PERIOD))
        environments_dfs[env_title] = env_dfs

        # timestep
        if len(timestep_codes) != 0:
            # prepare instants info
            instants_info = OrderedDict((
                (_timestep_month_, "month"),
                (_timestep_day_, "day"),
                (_timestep_hour_, "hour"),
                (_timestep_minute_, "minute"),
                (_timestep_dst_, "dst"),
                (_timestep_day_type_, "day_type")
            ))

            # create df
            df = pd.DataFrame.from_dict(OrderedDict((k, env_data[k]) for k in (tuple(instants_info) + timestep_codes)))

            # rename instant columns
            df.rename(inplace=True, columns=instants_info)

            # store if not empty (can happen, depends on environment)
            if len(df) > 0:
                env_dfs[TIMESTEP] = df

        # hourly
        if len(hourly_codes) != 0:
            # prepare instants info
            instants_info = OrderedDict((
                (_hourly_month_, "month"),
                (_hourly_day_, "day"),
                (_hourly_hour_, "hour"),
                (_hourly_dst_, "dst"),
                (_hourly_day_type_, "day_type")
            ))

            # create df
            df = pd.DataFrame.from_dict(OrderedDict((k, env_data[k]) for k in (tuple(instants_info) + hourly_codes)))

            # rename instant columns
            df.rename(inplace=True, columns=instants_info)

            # store if not empty (can happen, depends on environment)
            if len(df) > 0:
                env_dfs[HOURLY] = df

        # daily
        if len(daily_codes) != 0:
            # prepare instants info
            instants_info = OrderedDict((
                (_daily_month_, "month"),
                (_daily_day_, "day"),
                (_daily_dst_, "dst"),
                (_daily_day_type_, "day_type")
            ))

            # create df
            df = pd.DataFrame.from_dict(OrderedDict((k, env_data[k]) for k in (tuple(instants_info) + daily_codes)))

            # rename instant columns
            df.rename(inplace=True, columns=instants_info)

            # store if not empty (can happen, depends on environment)
            if len(df) > 0:
                env_dfs[DAILY] = df

        # monthly
        if len(monthly_codes) != 0:
            # instants info
            instants_info = {_monthly_month_: "month"}

            # create df
            df = pd.DataFrame.from_dict(dict((k, env_data[k]) for k in (tuple(instants_info) + monthly_codes)))

            # rename instant columns
            df.rename(inplace=True, columns=instants_info)

            # store if not empty (can happen, depends on environment)
            if len(df) > 0:
                env_dfs[MONTHLY] = df

        # annual
        if len(annual_codes) != 0:
            # instants info
            instants_info = {_annual_year_: "year"}

            # create df
            df = pd.DataFrame.from_dict(dict((k, env_data[k]) for k in (tuple(instants_info) + annual_codes)))

            # rename instant columns
            df.rename(inplace=True, columns=instants_info)

            # store if not empty (can happen, depends on environment)
            if len(df) > 0:
                env_dfs[ANNUAL] = df

        # run period
        if len(run_period_codes) != 0:
            df = pd.DataFrame.from_dict(dict((k, env_data[k]) for k in run_period_codes))
            # store if not empty (can happen, depends on environment)
            if len(df) > 0:
                env_dfs[RUN_PERIOD] = df

        # all: rename codes to columns fullname
        for df in env_dfs.values():
            if df is None:
                continue
            df.rename(columns=columns_rename, inplace=True)

    return environments, variables_info, environments_dfs
