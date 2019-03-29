import datetime as dt
import pandas as pd

from .parse_eso import TIMESTEP, HOURLY, DAILY, MONTHLY, ANNUAL, RUN_PERIOD


def switch_to_datetime_instants(df, start_year, eplus_frequency):
    """
    works inplace
    """
    # timestep -> monthly
    if eplus_frequency in (TIMESTEP, DAILY, HOURLY, MONTHLY):
        # prepare year switch
        if eplus_frequency in (TIMESTEP, HOURLY, DAILY):
            # print((df[["month", "day"]] - df[["month", "day"]].shift()) == pd.Series([-12, -31]))
            year_counter = (
                    (df[["month", "day"]] - df[["month", "day"]].shift()) ==
                    pd.Series(dict(month=12, day=-31))
            ).all(axis=1).cumsum()
        else:
            year_counter = ((df["month"] - df["month"].shift()) == -12).cumsum()

        # add year columns
        df["year"] = year_counter + start_year

        # create index
        columns = {
            TIMESTEP: ("year", "month", "day", "hour", "minute"),
            HOURLY: ("year", "month", "day", "hour"),
            DAILY: ("year", "month", "day"),
            MONTHLY: ("year", "month")
        }[eplus_frequency]
        if eplus_frequency == MONTHLY:
            df.index = df.apply(lambda x: dt.datetime(*tuple(x[k] for k in columns) + (1,)), axis=1)
        else:
            df.index = df.apply(lambda x: dt.datetime(*(x[k] for k in columns)), axis=1)

        # drop old columns
        df.drop(columns=list(columns), inplace=True)

        return df

    # annual
    if eplus_frequency == ANNUAL:
        # check first year
        if df["year"].iloc[0] != start_year:
            raise ValueError(
                f"Given start year ({start_year}) differs from annual output data first year ({df['year'].iloc[0]}),"
                f"can't switch to datetime instants.")
        df.index = df["year"].map(lambda x: dt.datetime(x, 1, 1))
        del df["year"]
        return df

    # run period
    if eplus_frequency == RUN_PERIOD:
        return df

    raise AssertionError("should not be here")
