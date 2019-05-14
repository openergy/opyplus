import collections
import datetime as dt

import pandas as pd


class DataContainer:
    instant_columns = None

    def __init__(self, variables):
        self.variables = {variable.code: variable for variable in variables}
        self.values = []
        self.current_row = None
        self.df = None

    def register_instant(self, *args):
        v = collections.OrderedDict((c, args[i]) for (i, c) in enumerate(self.instant_columns))
        v.update(collections.OrderedDict((code, None) for code in self.variables))
        self.values.append(v)
        self.current_row = v

    def register_value(self, code, value):
        self.current_row[code] = value

    def build_df(self):
        # create dataframe
        self.df = pd.DataFrame.from_records(self.values)

        # remove empty rows with no data
        self.df.dropna(how="all", subset=(c for c in self.df.columns if c not in self.instant_columns), inplace=True)

        # rename columns
        self.df.rename(
            columns=dict((var.code, f"{var.key_value.lower()},{var.name}") for var in self.variables.values()),
            inplace=True
        )
        # remove creation data (for memory usage)
        self.values = None
        self.current_row = None

    def create_datetime_index(self, start_year, freq=None):
        """
        works for all except run period
        """
        # remember temporary columns
        temporary_columns = []

        # calculate year counter
        if len({"month", "day"}.intersection(self.instant_columns)) == 2:
            year_counter = (
                    (self.df[["month", "day"]] - self.df[["month", "day"]].shift()) ==
                    pd.Series(dict(month=12, day=-31))
            ).all(axis=1).cumsum()
        elif "month" in self.instant_columns:
            year_counter = ((self.df["month"] - self.df["month"].shift()) == -12).cumsum()
        else:
            year_counter = pd.Series(data=[0]*len(self.df), index=self.df.index)

        # set temporary year
        self.df["year"] = year_counter + start_year
        temporary_columns.append("year")

        # add missing temporary columns
        for col, default in (
                ("month", 1),
                ("day", 1),
                ("hour", 0),
                ("minute", 0)
        ):
            if col not in self.instant_columns:
                self.df[col] = default
                temporary_columns.append(col)

        # create and set index
        self.df.index = self.df.apply(lambda x: dt.datetime(*(int(x[k]) for k in ("year", "month", "day", "hour", "minute"))), axis=1)

        # force freq (if relevant)





class SubHourlyDataContainer(DataContainer):
    instant_columns = (
        "month",
        "day",
        "hour",
        "minute",
        "end_minute",
        "dst",
        "day_type"
    )


class DailyDataContainer(DataContainer):
    instant_columns = (
        "month",
        "day",
        "dst",
        "day_type"
    )


class MonthlyDataContainer(DataContainer):
    instant_columns = ("month",)


class AnnualDataContainer(DataContainer):
    instant_columns = ("year",)


class RunPeriodDataContainer(DataContainer):
    instant_columns = ()

    def create_datetime_index(self, start_year):
        # not relevant
        return
