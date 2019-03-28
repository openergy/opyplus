import re
from collections import namedtuple, OrderedDict
import re

VariableInfo = namedtuple("VariableInfo", ("key_value", "name", "unit", "frequency", "info"))

Environment = namedtuple("Environment", ("environment_title", "latitude", "longitude", "time_zone", "elevation"))
TimestepInstant = namedtuple("TimestepInstant", ("month", "day", "hour", "minute", "dst", "day_type"))
DayInstant = namedtuple("DayInstant", ("month", "day", "dst", "day_type"))

comment_brackets_pattern = re.compile(r"\s\[[\w,]+\]")

# frequencies
TIMESTEP = "TimeStep"
HOURLY = "Hourly"
DAILY = "Daily"
MONTHLY = "Monthly"
ANNUAL = "Annual"
RUN_PERIOD = "RunPeriod"

# constants
EACH_CALL = "Each Call"

# constants
# BEGIN = "begin"
# DATA_D = "data_d"
# INDEX_L = "index_l"
# DST_L = "dst_l"
# DAY_TYPES_L = "day_types_l"


def parse_output(file_like):
    # ----------------------- LOAD METERS
    # VERSION
    row_l = next(file_like).spit(",")
    match = re.fullmatch(r"\s*Version\s*(\d+.\d+.\d+)-([\w\d]+)\s*", row_l[2])
    detailed_version = tuple(int(s) for s in match.group(1).split(".")) + (match.group(2),)

    # for eplus >= 9, code 6 is for annual variables (did not exist before)
    annual_code = None if detailed_version[0] < 9 else 6
    max_data_dict_info_code = 5 if annual_code is None else annual_code

    # DATA DICTIONARY
    variables_info = {  # {frequency: {code: Variable, ....
        TIMESTEP: {},
        HOURLY: {},
        DAILY: {},
        MONTHLY: {},
        ANNUAL: {},
        RUN_PERIOD: {}
    }

    while True:
        row = next(file_like)

        # leave if finished
        if row == "End of Data Dictionary":
            break

        # get code and vars_num
        code, vars_num, other = row.split(",", 2)
        code = int(code)
        vars_num = int(vars_num)

        # continue if concerns dictionary info (is always the same and is documented, no need to parse)
        if code <= max_data_dict_info_code:
            continue

        # split content and comment
        content, comment = other.split(" !")

        # parse content
        key_value, var_name = content.split(",")
        var_name, unit = var_name.split(" [")
        unit = unit[:-1]

        # parse comment
        if vars_num != 1:  # remove brackets if relevant
            comment = re.sub(comment_brackets_pattern, "", content)
        timestep_and_or_info = comment.split(" ,")

        # frequency
        frequency = timestep_and_or_info[0]
        if frequency == EACH_CALL:
            frequency = TIMESTEP

        # info
        try:
            info = timestep_and_or_info[1]
        except IndexError:
            info = ""

        # store variable info
        variables_info[frequency][code] = VariableInfo(
            key_value,
            var_name,
            unit,
            frequency,
            info
        )

    # ------------------------ LOAD DATA
    current_env_data = None
    # shared local variables
    data_d, index_l, day_types_l, dst_l = None, None, None, None  # dataframe environments
    month_num, day_num, hour_num, end_minute_num, day_type, dst = None, None, None, None, None, None

    # global variables
    environments = OrderedDict()  # {environment_name: {environment: ,

    # loop
    while True:
        row = next(file_like)

        # leave if finished
        if row == "End of Data":
            break

        # find item num
        code, other = row.split(",", 1)
        code = int(code)

        if code == 1:  # new environment
            other = other.split(",")
            env = Environment(
                other[0],
                float(other[1]),
                float(other[2]),
                float(other[3]),
                float(other[4])
            )

            current_env_data = dict(  # values: [{code: value, ..., ...
                environment=env,
                TIMESTEP=dict(instants=[], values=[]),
                DAILY=dict(instants=[], values=[]),
                MONTHLY=dict(months=[], values=[]),
                ANNUAL=dict(years=[], values=[]),  # will only be used for >= 9.0.1
                RUN_PERIOD=dict(values=[])
            )

            environments[env.environment_title] = current_env_data

        elif code == 2:  # timestep (and hourly) data
            # 0-sim_day, 1-month_num, 2-day_num, 3-dst, 4-hour_num, 5-start_minute, 6-end_minute, 7-day_type
            other = other.split(",")
            current_env_data[TIMESTEP]["instants"].append(TimestepInstant(
                int(other[1]),
                int(other[2]),
                int(other[4]),
                int(other[5]),
                int(other[3]),
                other[7]
            ))
            current_values = dict()
            current_env_data[TIMESTEP]["values"].append(current_values)

        elif code == 3:  # daily
            # 0-sim_day, 1-month_num, 2-day_num, 3-dst, 4-day_type
            other = other.split(",")
            current_env_data[DAILY]["instants"].append(DayInstant(
                int(other[1]),
                int(other[2]),
                int(other[3]),
                other[4]
            ))
            current_values = dict()
            current_env_data[DAILY]["values"].append(current_values)

        elif code == 4:  # monthly
            other = other.split(",")
            current_env_data[MONTHLY]["months"].append(int(other[1]))
            current_values = dict()
            current_env_data[MONTHLY]["values"].append(current_values)

        elif code == 5:  # run period data
            current_values = dict()
            current_env_data[RUN_PERIOD]["values"].append(current_values)

        elif code == annual_code:  # will only be used for >= 9.0.1
            current_env_data[ANNUAL]["years"].append(int(other))
            current_values = dict()
            current_env_data[ANNUAL]["values"].append(current_values)

        if code > max_data_dict_info_code:  # value to store
            raise Exception("continue here")
            try:
                val = float(other)
            except ValueError:  # happens for 'RunPeriod' or 'Monthly' time step
                val = float(other.split(",")[0])  # we don't parse min and max

            # value has been parsed correctly
            try:
                data_d[code].append(val)  # data_d belongs to current env
            except (TypeError, KeyError):
                # data_d has not been initialized. Happens for first value of item_num 2, if interval is not known yet
                # find interval
                for ep_freq in (HOURLY, TIMESTEP, DETAILED):
                    if code in variables_info[ep_freq]:
                        break
                else:
                    raise KeyError("Interval not found: '%s'." % row)

                # activate item
                data_d = raw_env_d[ep_freq][DATA_D]
                index_l = raw_env_d[ep_freq][INDEX_L]
                day_types_l = raw_env_d[ep_freq][DAY_TYPES_L]
                dst_l = raw_env_d[ep_freq][DST_L]

                # store
                index_l.append((month_num, day_num, hour_num, end_minute_num))
                day_types_l.append(day_type)
                dst_l.append(dst)

                # append as tried before
                data_d[code].append(val)











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
        for ep_freq in (TIMESTEP, HOURLY, DAILY, MONTHLY, RUN_PERIOD):
            if ep_freq not in raw_env_d:  # no data
                continue

            # CREATE
            # index
            index_l = raw_env_d[ep_freq][INDEX_L]
            if len(index_l) == 0:  # no data
                continue

            if ep_freq in (DETAILED, TIMESTEP, HOURLY, DAILY):  # multi-index
                names = {
                    DETAILED: ["month", "day", "hour", "minute"],
                    TIMESTEP: ["month", "day", "hour", "minute"],
                    HOURLY: ["month", "day", "hour", "minute"],
                    DAILY: ["month", "day"]
                }[ep_freq]
                index = pd.MultiIndex.from_tuples(index_l, names=names)
            else:
                index = pd.Index(index_l)

            # dataframe
            data_d = raw_env_d[ep_freq][DATA_D]
            df = pd.DataFrame(data_d, index=index)
            df.rename(columns=dict([(k, variables_info[ep_freq][k][0]) for k in variables_info[ep_freq]]), inplace=True)

            # add dst and day_type if available
            if ep_freq in (TIMESTEP, HOURLY, DAILY):
                df.insert(0, "dst", raw_env_d[ep_freq]["dst_l"])
                df.insert(0, "day_type", raw_env_d[ep_freq]["day_types_l"])

            # STORE
            if not env_name in envs_d:
                envs_d[env_name] = {}
            if ep_freq in envs_d[env_name]:
                logger.error("Same environment has two identical time steps: '%s'." % raw_env_d[1])
            envs_d[env_name][ep_freq] = df

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
