import io
import re

import pandas as pd
from pandas.util.testing import assert_index_equal

from oplus.configuration import CONF
from oplus.util import EPlusDt, get_start_dt, get_copyright_comment, sort_df


EPW_COLUMNS = (
    "year",
    "month",
    "day",
    "hour",
    "minute",
    "datasource",
    "drybulb",
    "dewpoint",
    "relhum",
    "atmos_pressure",
    "exthorrad",
    "extdirrad",
    "horirsky",
    "glohorrad",
    "dirnorrad",
    "difhorrad",
    "glohorillum",
    "dirnorillum",
    "difhorillum",
    "zenlum",
    "winddir",
    "windspd",
    "totskycvr",
    "opaqskycvr",
    "visibility",
    "ceiling_hgt",
    "presweathobs",
    "presweathcodes",
    "precip_wtr",
    "aerosol_opt_depth",
    "snowdepth",
    "days_last_snow",
    "albedo",
    "liq_precip_depth",
    "liq_precip_rate"
)

WEEK_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class EpwHeader:
    LOCATION = 0
    DESIGN_CONDITIONS = 1
    TYPICAL_EXTREME_PERIODS = 2
    GROUND_TEMPERATURES = 3
    HOLIDAYS_DAYLIGHT_SAVINGS = 4
    COMMENTS_1 = 5
    COMMENTS_2 = 6
    DATA_PERIODS = 7

    @staticmethod
    def copyright_comment():
        return get_copyright_comment(multi_lines=False)

    def __init__(self, header_s):
        self._l2 = []
        for line_s in header_s.strip().split("\n"):
            self._l2.append([cell.strip() for cell in line_s.split(",")])
        # check
        if len(self._l2[self.DATA_PERIODS]) != 7:
            raise ValueError("'DATA PERIODS' row must have 7 cells.")
        if self._l2[self.DATA_PERIODS][0] != "DATA PERIODS":
            raise ValueError("Last line of header must be 'DATA PERIODS'.")
        if self._l2[self.DATA_PERIODS][1] != "1":
            raise NotImplementedError("Can only manage epws with one data period.")
        if self._l2[self.DATA_PERIODS][2] != "1":
            raise NotImplementedError("Can only manage hourly epws.")

    def to_str(self, add_copyright=True):
        l2 = []
        if add_copyright:
            for i, row in enumerate(self._l2):
                if add_copyright and (i == self.COMMENTS_1):
                    copyright_comment = self.copyright_comment()
                    row = row.copy()
                    if not copyright_comment in row[1]:
                        row[1] = "%s; %s" % (copyright_comment, row[1])
                l2.append(row)
        else:
            l2 = self._l2
        return "\n".join([", ".join(row) for row in l2])

    @property
    def start(self):
        """
        (month, day)
        """
        return self._l2[self.DATA_PERIODS][5].split(",").map(int)

    @start.setter
    def start(self, value):
        self._l2[self.DATA_PERIODS][5] = "%s/%s" % value

    @property
    def end(self):
        """
        (month, day)
        """
        return self._l2[self.DATA_PERIODS][6].split(",").map(int)

    @end.setter
    def end(self, value):
        self._l2[self.DATA_PERIODS][6] = "%s/%s" % value

    @property
    def freq(self):
        return {"1": "H"}[self._l2[self.DATA_PERIODS][2]]


class Epw:
    epw_header_cls = EpwHeader

    @classmethod
    def get_epw_or_path(cls, epw_or_path, logger_name=None, encoding=None):
        if isinstance(epw_or_path, str):
            return cls(epw_or_path, logger_name=logger_name, encoding=encoding)
        elif isinstance(epw_or_path, cls):
            return epw_or_path
        raise ValueError("'epw_or_path' must be an EPW or path.  Given object: '%s', type: '%s'." %
                       (epw_or_path, type(epw_or_path)))

    def __init__(self, path_or_buffer, logger_name=None, encoding=None, start=None):
        self._logger_name = logger_name
        self._encoding = encoding
        if isinstance(path_or_buffer, str):
            with open(path_or_buffer, encoding=CONF.encoding if self._encoding is None else self._encoding) as f:
                self._df, self._header = parse_epw(f, logger_name=logger_name, encoding=encoding)
        else:
            self._df, self._header = parse_epw(path_or_buffer, logger_name=logger_name, encoding=encoding)

        self._start_dt = None if start is None else get_start_dt(start)

    @property
    def header(self):
        return self._header

    @property
    def freq(self):
        return self._header.freq

    def save_as(self, file_or_path, add_copyright=True):
        is_path = isinstance(file_or_path, str)

        # header
        content = self._header.to_str(add_copyright=add_copyright)

        # data
        _f = io.StringIO()
        self._df.reset_index().to_csv(_f, header=False, index=False)
        content += "\n" + _f.getvalue()

        # write to f
        f = (open(file_or_path, "w", encoding=CONF.encoding if self._encoding is None else self._encoding)
             if is_path else file_or_path)

        f.write(content)

    def set_start(self, start):
        self._start_dt = get_start_dt(start)

    def df(self, start=None, datetime_index=None):
        """
        order: will impose a freq, should not be used with reference climate (where years may differ by month)
        """
        # start_dt and datetime index
        if start is None:
            start_dt = self._start_dt
        else:
            start_dt = get_start_dt(start)

        if datetime_index is None:
            datetime_index = start_dt is not None
        if (datetime_index is True) and (start_dt is None):
            # we get first value as start_dt
            i0 = self._df.index[0]
            start_dt = EPlusDt(i0[1], i0[2], i0[3], i0[4]).datetime(i0[0])

        # data frame
        df = self._df.copy()

        if not datetime_index:  # return if multi-index
            return df

        # manage datetime df
        start_standard_dt = EPlusDt.from_datetime(start_dt).standard_dt

        def index_to_dt(i):
            eplusdt = EPlusDt(i[1], i[2], i[3], i[4])
            _year = start_dt.year + 1 if eplusdt.standard_dt <= start_standard_dt else start_dt.year
            return eplusdt.datetime(_year)

        df.index = df.index.map(index_to_dt)
        df = sort_df(df)
        df = df.reindex(pd.date_range(df.index[0], df.index[-1], freq=self.freq))

        return df

    def set_df(self, value):
        if not isinstance(value, pd.DataFrame):
            raise ValueError("df must be a DataFrame")
        assert_index_equal(value.index, self._df.index)
        assert_index_equal(value.columns, self._df.columns)


def parse_epw(file_like, encoding=None, logger_name=None):
    header_s = ""

    # header
    for line_s in file_like:
        header_s += line_s
        if re.match("^DATA PERIODS", line_s) is not None:
            break
    header = EpwHeader(header_s)

    # data
    df = pd.read_csv(file_like, header=None, low_memory=False, encoding=encoding)
    df.columns = EPW_COLUMNS[:len(df.columns)]
    df.index = pd.MultiIndex.from_arrays([df[c] for c in df.columns[:5]])
    for c in df.columns[:5].tolist():
        del df[c]

    return df, header
