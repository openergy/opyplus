import datetime as dt

import pandas as pd
from pandas.util.testing import assert_index_equal


class DataContainer:
    def __init__(self, variables, freq, instant_columns, pandas_freq=None):
        """
        Parameters
        ----------
        variables
        instant_columns
        pandas_freq: str or None, default None
            pandas freq, or '?' (for timestep), or None (for each call and run period)
        """
        self.freq = freq
        self.instant_columns = instant_columns
        self.variables_by_code = {variable.code: variable for variable in variables}
        self.pandas_freq = pandas_freq
        self.values = []
        self.current_row = None
        self.df = None

    def __str__(self):
        msg = "DataContainer\n"
        msg += f"  freq: {self.freq}\n"
        return msg

    def register_instant(self, *args):
        v = {c: args[i] for (i, c) in enumerate(self.instant_columns)}
        # v.update({code: None for code in self.variables_by_code})
        self.values.append(v)
        self.current_row = v

    def register_value(self, code, value):
        self.current_row[code] = value

    def build_df(self):
        # create dataframe
        self.df = pd.DataFrame.from_records(
            self.values,
            columns=list(self.instant_columns) + list(self.variables_by_code)
        )

        # remove empty rows with no data
        self.df.dropna(how="all", subset=(c for c in self.df.columns if c not in self.instant_columns), inplace=True)

        # rename columns
        self.df.rename(
            columns=dict((var.code, f"{var.key_value.lower()},{var.name}") for var in self.variables_by_code.values()),
            inplace=True
        )
        # remove creation data (for memory usage)
        self.values = None
        self.current_row = None

    def create_datetime_index(self, start_year):
        """
        works for all except run period
        """
        # manage year
        if "year" not in self.instant_columns:
            # calculate year counter
            if len({"month", "day"}.intersection(self.instant_columns)) == 2:
                year_counter = (
                        (self.df[["month", "day"]] - self.df[["month", "day"]].shift()) ==
                        pd.Series(dict(month=-11, day=-30))
                ).all(axis=1).cumsum()
            elif "month" in self.instant_columns:
                year_counter = ((self.df["month"] - self.df["month"].shift()) == -12).cumsum()
            else:
                year_counter = pd.Series(data=[0]*len(self.df), index=self.df.index)

            # set temporary year
            self.df["year"] = year_counter + start_year
        else:
            # check first year is start_year
            if (len(self.df) > 0) and (self.df["year"].iloc[0] != start_year):
                raise ValueError(
                    f"Given start year ({start_year}) differs from annual output data first year "
                    f"({self.df['year'].iloc[0]}), can't switch to datetime instants."
                )

        # manage other datetime columns (defaults are used when column is not relevant for given freq)
        for col, default in (
                ("month", 1),
                ("day", 1),
                ("hour", 0),
                ("minute", 0)
        ):
            if col not in self.instant_columns:
                self.df[col] = default

        # create and set index
        self.df.index = self.df.apply(
            lambda x: dt.datetime(*(int(x[k]) for k in ("year", "month", "day", "hour", "minute"))),
            axis=1
        )

        # force freq (if relevant)
        old_index = self.df.index
        if self.pandas_freq == "?":
            # find freq and force
            ts = self.df.index[1] - self.df.index[0]
            self.df = self.df.asfreq(ts)
        elif self.pandas_freq is not None:
            self.df = self.df.asfreq(self.pandas_freq)

        # check index did not change (because of leap year problems)
        try:
            assert_index_equal(self.df.index, old_index)
        except AssertionError:
            raise ValueError(
                f"Couldn't convert to datetime instants (frequency: {self.freq}). Probable cause : "
                f"given start year ({start_year}) is incorrect and data can't match because of leap year issues."
            ) from None

        # drop temporary columns
        self.df.drop(
            columns=list(c for c in ("year", "month", "day", "hour", "minute") if c not in self.instant_columns),
            inplace=True
        )
