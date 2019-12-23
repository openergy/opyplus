import pandas as pd

from opyplus import CONF
from .weather_data import WeatherData, COLUMNS
from .design_condition import DesignCondition
from .typical_extreme_period import TypicalExtremePeriod
from .ground_temperature import GroundTemperature


def _get_row_l(row):
    return [cell.strip() for cell in row.split(",")]


def parse_epw(file_like) -> WeatherData:
    # parse header

    # location
    location_row_l = _get_row_l(next(file_like))
    (
        _,
        city,
        state_province_region,
        country,
        source,
        wmo,
        latitude,
        longitude,
        timezone_offset,
        elevation
    ) = location_row_l[:10]

    # design conditions
    design_conditions_row_l = _get_row_l(next(file_like))
    try:
        design_condition_source = design_conditions_row_l[2]
    except IndexError:
        design_condition_source = ""
    design_conditions = []
    current_dc = None
    for cell in design_conditions_row_l[3:]:
        if cell == "":
            continue
        try:
            value = float(cell)
            current_dc.values.append(value)
        except ValueError:
            # new design conditions
            current_dc = DesignCondition(cell, [])
            design_conditions.append(current_dc)

    # typical/extreme periods
    typical_extreme_periods_row_l = _get_row_l(next(file_like))
    typical_extreme_periods = []
    cycles_l = typical_extreme_periods_row_l[2:]
    cycles_l_len = len(cycles_l)
    for i in range(0, cycles_l_len, 4):
        if i + 3 >= cycles_l_len:
            break
        typical_extreme_periods.append(TypicalExtremePeriod(*[cycles_l[k] for k in range(i, i + 4)]))

    # ground temperatures
    ground_temperatures_row_l = _get_row_l(next(file_like))
    ground_temperatures = []
    cycles_l = ground_temperatures_row_l[2:]
    cycles_l_len = len(cycles_l)
    for i in range(0, cycles_l_len, 16):
        if i + 15 >= cycles_l_len:
            break
        ground_temperatures.append(GroundTemperature(
            *[cycles_l[k] for k in range(i, i + 4)],
            cycles_l[i + 4:i + 16]
        ))

    # holidays/daylight savings
    holidays_daylight_savings_row_l = _get_row_l(next(file_like))
    (
        _,
        leap_year_observed,
        daylight_savings_start_day,
        daylight_savings_end_day
    ) = holidays_daylight_savings_row_l[:4]
    holidays = []
    cycles_l = holidays_daylight_savings_row_l[5:]
    cycles_l_len = len(cycles_l)
    for i in range(0, cycles_l_len, 2):
        if i + 1 >= cycles_l_len:
            break
        holidays.append([cycles_l[0], cycles_l[1]])

    # comments
    comments_1_row_l = _get_row_l(next(file_like))
    comments_1 = comments_1_row_l[1]
    comments_2_row_l = _get_row_l(next(file_like))
    comments_2 = comments_2_row_l[1]

    # data period
    data_period_row_l = _get_row_l(next(file_like))
    start_day_of_week = data_period_row_l[4]
    if start_day_of_week == "":
        start_day_of_week = None

    # load dataframe
    weather_series = pd.read_csv(file_like, header=None, encoding=CONF.encoding)
    weather_series.columns = list(COLUMNS)[:len(weather_series.columns)]

    return WeatherData(
        weather_series,
        latitude,
        longitude,
        timezone_offset,
        elevation,
        city=city,
        state_province_region=state_province_region,
        country=country,
        source=source,
        wmo=wmo,
        design_conditions_source=design_condition_source,
        design_conditions=design_conditions,
        typical_extreme_periods=typical_extreme_periods,
        ground_temperatures=ground_temperatures,
        leap_year_observed=leap_year_observed,
        daylight_savings_start_day=daylight_savings_start_day,
        daylight_savings_end_day=daylight_savings_end_day,
        holidays=holidays,
        comments_1=comments_1,
        comments_2=comments_2,
        start_day_of_week=start_day_of_week
    )
