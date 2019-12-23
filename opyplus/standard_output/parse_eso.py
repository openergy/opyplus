import collections
import re
import time

from .output_environment import OutputEnvironment, EACH_CALL, DAILY, MONTHLY, ANNUAL, RUN_PERIOD, SUB_HOURLY, \
    FREQUENCIES
from .output_variable import OutputVariable

comment_brackets_pattern = re.compile(r"\s\[[\w,]+\]")

# other
METER = "Meter"


def parse_eso(file_like, print_function=lambda x: None):
    """
    start and end instants are given in eso. we only use start instant because we want to work in left convention
    """
    # ----------------------- LOAD METERS
    # VERSION
    row_s = next(file_like)
    row_l = row_s.split(",")
    if len(row_l) == 4:  # most common syntax
        # ex: Program Version,EnergyPlus, Version 9.2.0-921312fa1d, YMD=2019.10.30 13:21
        version_s = row_l[2]
        match = re.fullmatch(r"\s*Version\s*(\d+\.\d+\.\d+)-([\w\d]+)\s*", version_s)
    elif len(row_l) == 3:  # other syntax
        # Program Version,EnergyPlus-Windows-64 8.0.0.008, YMD=2019.10.31 21:19
        version_s = row_l[1]
        match = re.fullmatch(r"\s*EnergyPlus-[\w\d\-]+\s(\d+\.\d+\.\d+)\.([\d\w]+)\s*", version_s)
    else:
        match = None
    if match is None:
        raise RuntimeError(f"unknown version format: '{row_s}'")
    detailed_version = tuple(int(s) for s in match.group(1).split(".")) + (match.group(2),)

    # for eplus >= 8.9.0, code 6 is for annual variables (did not exist before)
    annual_code = None if detailed_version[:2] < (8, 9) else "6"
    max_data_dict_info_code_int = 5 if annual_code is None else int(annual_code)

    # variables
    variables_by_freq = dict()  # timestep: variables

    # initialize timer
    start = time.time()
    row_num = 1
    while True:
        if time.time() - start > 60:
            start = time.time()
            print_function(f"parsing E+ eso, row: {row_num}")

        row_num += 1
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
        content, comment = other.split("!", 1)

        # parse content
        content_l = content.split(",")
        if len(content_l) == 2:
            key_value, var_name = content_l
            key_value = key_value.strip().lower()  # no retaincase
            var_name, unit = var_name.split("[")
            var_name = var_name.strip()
            unit = unit.strip()[:-1]
        elif len(content_l) == 1:  # may only have one element (for example Custom:Meter)
            key_value = content.strip()
            var_name = METER
            key_value, unit = key_value.split("[")

            key_value = key_value.strip().lower()  # no retaincase
            unit = unit.strip()[:-1]
        else:
            raise RuntimeError(f"unknown syntax for row {row_num}: '{row}'")

        # parse comment
        if vars_num != 1:  # remove brackets if relevant
            comment = re.sub(comment_brackets_pattern, "", comment)
        timestep_and_or_info = comment.split(",")

        # frequency
        frequency = timestep_and_or_info[0].lower().strip()  # no retaincase, we replace with _ for each_call
        if frequency == "each call":
            frequency = EACH_CALL  # we add an underscore
        elif frequency == "runperiod":
            frequency = RUN_PERIOD  # we add an underscore

        # info
        try:
            info = timestep_and_or_info[1]
        except IndexError:
            info = ""

        # create variable frequency if needed
        if frequency not in variables_by_freq:
            variables_by_freq[frequency] = []

        # store variable info
        variables_by_freq[frequency].append(OutputVariable(
            code,
            key_value,
            var_name,
            unit,
            frequency,
            info
        ))

    # sort variables by freq
    variables_by_freq = collections.OrderedDict(
        (freq, variables_by_freq[freq]) for freq in
        sorted(variables_by_freq, key=lambda freq: FREQUENCIES.index(freq))
    )

    # ------------------------ LOAD DATA
    # global variables
    environments_by_title = collections.OrderedDict()  # {environment_title: environment: ,

    # current variables
    env = None

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
            env = OutputEnvironment(
                other[0].lower(),
                float(other[1]),
                float(other[2]),
                float(other[3]),
                float(other[4]),
                variables_by_freq
            )
            environments_by_title[env.title] = env

            # prepare and store environment data
            # data: { code: values, ...

        elif code == "2":  # timestep (and hourly) data
            # 0-sim_day, 1-month_num, 2-day_num, 3-dst, 4-hour_num, 5-start_minute, 6-end_minute, 7-day_type
            other = other.split(",")
            month = int(other[1])
            day = int(other[2])
            hour = int(other[4]) - 1
            minute = int(float(other[5]))
            end_minute = int(float(other[6]))
            dst = int(other[3])
            day_type = other[7]

            env._dev_register_instant(
                SUB_HOURLY,
                month,
                day,
                hour,
                minute,
                end_minute,
                dst,
                day_type
            )

        elif code == "3":  # daily
            # 0-sim_day, 1-month_num, 2-day_num, 3-dst, 4-day_type
            other = other.split(",")
            env._dev_register_instant(
                DAILY,
                int(other[1]),
                int(other[2]),
                int(other[3]),
                other[4]
            )

        elif code == "4":  # monthly
            other = other.split(",")
            env._dev_register_instant(MONTHLY, int(other[1]))

        elif code == "5":  # run period data
            # nothing to do
            env._dev_register_instant(RUN_PERIOD)

        elif code == annual_code:  # will only be used for >= 9.0.1
            env._dev_register_instant(ANNUAL, int(other))

        else:  # value to store
            # parse
            try:
                val = float(other)
            except ValueError:  # happens for 'RunPeriod' or 'Monthly' time step
                val = float(other.split(",")[0])  # we don't parse min and max

            # store
            env._dev_register_value(code, val)

    # build dataframes
    for env in environments_by_title.values():
        env._dev_build_dfs()

    # return
    return environments_by_title, variables_by_freq
