import re

# environments
DETAILED = "Detailed"
TIMESTEP = "TimeStep"
HOURLY = "Hourly"
DAILY = "Daily"
MONTHLY = "Monthly"
ANNUAL = "Annual"
RUN_PERIOD = "RunPeriod"

# constants
BEGIN = "begin"
DATA_D = "data_d"
INDEX_L = "index_l"
DST_L = "dst_l"
DAY_TYPES_L = "day_types_l"


def parse_output(file_like):
    # ----------------------- LOAD METERS
    # INFO
    row = next(file_like)
    row_l = row.spit(",")
    detailed_version = re.fullmatch(r"\s*Version\s*(\d+.\d+.\d+-[\w\d]+)\s*", row_l[2]).group(1)
    version_str = re.fullmatch(r"(\d+.\d+.\d+)-[\w\d]+", detailed_version).group(1)
    version = tuple(int(s) for s in version_str.split("."))

    info = dict(
        eplus_version=version,
        eplus_detailed_version=detailed_version,
        instant=row_l[3].strip()
    )

    # prepare

    # for eplus >= 9, code 6 is for annual variables (did not exist before)
    max_data_dict_info_code = 5 if version[0] < 9 else 6

    # DATA DICTIONARY
    codes_d = {
        DETAILED: {},
        TIMESTEP: {},
        HOURLY: {},
        DAILY: {},
        MONTHLY: {},
        ANNUAL: {},
        RUN_PERIOD: {}
    }

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

        # we only look for output variables, not  data dictionary info
        if report_code > max_data_dict_info_code:
            for (interval, pattern) in (
                    (DETAILED, "Each Call"),
                    (TIMESTEP, TIMESTEP),
                    (HOURLY, HOURLY),
                    (DAILY, DAILY),
                    (MONTHLY, MONTHLY),
                    (RUN_PERIOD, RUN_PERIOD)
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

        if item_num > max_data_dict_info_code:  # value to store
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
                for interval in (HOURLY, TIMESTEP, DETAILED):
                    if item_num in codes_d[interval]:
                        break
                else:
                    raise KeyError("Interval not found: '%s'." % line_s)

                # activate item
                data_d = raw_env_d[interval][DATA_D]
                index_l = raw_env_d[interval][INDEX_L]
                day_types_l = raw_env_d[interval][DAY_TYPES_L]
                dst_l = raw_env_d[interval][DST_L]

                # store
                index_l.append((month_num, day_num, hour_num, end_minute_num))
                day_types_l.append(day_type)
                dst_l.append(dst)

                # append as tried before
                data_d[item_num].append(val)

        elif item_num == 5:  # run period data
            # activate env
            data_d = raw_env_d[RUN_PERIOD][DATA_D]
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
            data_d = raw_env_d[DAILY][DATA_D]
            index_l = raw_env_d[DAILY][INDEX_L]
            dst_l = raw_env_d[DAILY][DST_L]
            day_types_l = raw_env_d[DAILY][DAY_TYPES_L]

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
            data_d = raw_env_d[MONTHLY]["data_d"]
            index_l = raw_env_d[MONTHLY]["index_l"]
            dst_l, day_types_l = None, None  # not used in monthly environment

            # parse
            # 0-sim_day, 1-month_num
            right_l = right_s.split(",")
            month_num = int(right_l[1])

            # store
            index_l.append(month_num)

        elif item_num == 1:  # new environment
            raw_env_d = {BEGIN: line_s}
            for interval in (DETAILED, TIMESTEP, HOURLY, DAILY, MONTHLY, RUN_PERIOD):  # meters and index
                if len(codes_d[interval]) == 0:  # no meters
                    continue
                raw_env_d[interval] = dict(data_d=dict([(k, []) for k in codes_d[interval]]), index_l=[])
                if interval == RUN_PERIOD:
                    raw_env_d[interval][INDEX_L] = ["Total"]
                if interval in (DETAILED, TIMESTEP, HOURLY, DAILY):  # dst, day type
                    raw_env_d[interval][DST_L] = []
                    raw_env_d[interval][DAY_TYPES_L] = []
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
        for interval in (TIMESTEP, HOURLY, DAILY, MONTHLY, RUN_PERIOD):
            if interval not in raw_env_d:  # no data
                continue

            # CREATE
            # index
            index_l = raw_env_d[interval][INDEX_L]
            if len(index_l) == 0:  # no data
                continue

            if interval in (DETAILED, TIMESTEP, HOURLY, DAILY):  # multi-index
                names = {
                    DETAILED: ["month", "day", "hour", "minute"],
                    TIMESTEP: ["month", "day", "hour", "minute"],
                    HOURLY: ["month", "day", "hour", "minute"],
                    DAILY: ["month", "day"]
                }[interval]
                index = pd.MultiIndex.from_tuples(index_l, names=names)
            else:
                index = pd.Index(index_l)

            # dataframe
            data_d = raw_env_d[interval][DATA_D]
            df = pd.DataFrame(data_d, index=index)
            df.rename(columns=dict([(k, codes_d[interval][k][0]) for k in codes_d[interval]]), inplace=True)

            # add dst and day_type if available
            if interval in (TIMESTEP, HOURLY, DAILY):
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
