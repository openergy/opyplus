import re

DETAILED = "Detailed"
TIMESTEP = "TimeStep"
HOURLY = "Hourly"
DAILY = "Daily"
MONTHLY = "Monthly"
ANNUAL = "Annual"
RUN_PERIOD = "RunPeriod"


def parse_eso(file_like):
    # VERSION
    row_l = next(file_like).spit(",")
    match = re.fullmatch(r"\s*Version\s*(\d+.\d+.\d+)-([\w\d]+)\s*", row_l[2])
    detailed_version = tuple(int(s) for s in match.group(1).split(".")) + (match.group(2), )

    # for eplus >= 9, code 6 is for annual variables (did not exist before)
    max_data_dict_info_code = 5 if detailed_version[0] < 9 else 6

    # DATA DICT
    codes_info = dict()  # code_str: {index: , short_name, unit, timestep,
    while True:
        row = next(file_like)
        # quit if end of data dictionary
        if row == "End of Data Dictionary":
            break

        # prepare row
        row_l = row.split("!")
        if len(row_l) == 1:
            content_s, comment = row_l[0], ""
        else:
            content_s, comment = row_l
            comment = comment.strip()
        content_s = content_s.strip()

        # report code
        content_l = content_s.split(",", 2)
        report_code, items_number, value_s = content_l[0], int(content_l[1]), content_l[2]  # we only keep first value

        # we only look for output variables, not  data dictionary info
        if report_code > max_data_dict_info_code:
            for (interval, pattern) in (
                    (DETAILED, "Each Call"),
                    (TIMESTEP, TIMESTEP),
                    (HOURLY, HOURLY),
                    (DAILY, DAILY),
                    (MONTHLY, MONTHLY),
                    (ANNUAL, ANNUAL),
                    (RUN_PERIOD, RUN_PERIOD)
            ):
                if pattern in comment:
                    break
            else:
                raise KeyError("Interval not found: '%s'" % row)


        codes_d[interval][report_code] = []
        for var_s in vars_l_s.split(",", items_number - 1):
            try:
                var_name, right_s = var_s.split("[")
                var_unit = right_s[:-1].strip()
            except ValueError:
                var_name, var_unit = var_s, None
            codes_d[interval][report_code] = (var_name.strip(), var_unit)

