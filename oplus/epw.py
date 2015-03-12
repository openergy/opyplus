import os
import io
import re

import pandas as pd
from pandas.util.testing import assert_index_equal

from oplus.configuration import CONFIG
from oplus.util import EPlusDt

default_logger_name = __name__ if CONFIG.logger_name is None else CONFIG.logger_name


class EPWError(Exception):
    pass


EPW_COLUMNS = ["year", "month", "day", "hour", "minute", "datasource",
               "drybulb", "dewpoint", "relhum", "atmos_pressure", "exthorrad",
               "extdirrad", "horirsky", "glohorrad", "dirnorrad", "difhorrad",
               "glohorillum", "dirnorillum", "difhorillum", "zenlum", "winddir",
               "windspd", "totskycvr", "opaqskycvr", "visibility", "ceiling_hgt", "presweathobs",
               "presweathcodes", "precip_wtr", "aerosol_opt_depth", "snowdepth", "days_last_snow",
               "albedo", "liq_precip_depth", "liq_precip_rate"]

WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class EPW:
    @classmethod
    def get_epw_or_path(cls, epw_or_path, logger_name=None, encoding=None):
        if isinstance(epw_or_path, str):
            return cls(epw_or_path, logger_name=logger_name, encoding=encoding)
        elif isinstance(epw_or_path, cls):
            return epw_or_path
        raise EPWError("'epw_or_path' must be an EPW or path.  Given object: '%s', type: '%s'." %
                       (epw_or_path, type(epw_or_path)))

    def __init__(self, path_or_buffer, logger_name=None, encoding=None):
        self._logger_name = logger_name
        self._encoding = encoding
        if isinstance(path_or_buffer, str):
            with open(path_or_buffer, encoding=CONFIG.encoding if self._encoding is None else self._encoding) as f:
                self._df, self._header = parse_epw(f, logger_name=logger_name, encoding=encoding)
        else:
            self._df, self._header = parse_epw(path_or_buffer, logger_name=logger_name, encoding=encoding)
        # self._logger_name = logger_name
        # self._encoding = encoding

    @property
    def header(self):
        return self._header

    @property
    def freq(self):
        return self._header.freq

    def save_as(self, file_or_path):
        is_path = isinstance(file_or_path, str)

        # header
        content = self._header.to_str()

        # data
        # todo: make public function
        _f = io.StringIO()
        self._df.reset_index().to_csv(_f, header=False, index=False)
        content += "\n" + _f.getvalue()

        # write to f
        f = (open(file_or_path, "w", encoding=CONFIG.encoding if self._encoding is None else self._encoding)
             if is_path else file_or_path)

        f.write(content)

    def df(self, start_dt=None, datetime_index=False, impose_freq=True):
        # todo: implement
        """
        order: will impose a freq, should not be used with reference climate (where years may differ by month)
        """
        if datetime_index is True:
            _df = self._df.copy()
            _df.index = _df.index.map(lambda x: EPlusDt(x[1], x[2], x[3], x[4]).datetime(x[0]))
            if impose_freq:
                _df = _df.reindex(pd.date_range(_df.index.min(), _df.index.max(), freq=self.freq))
            return _df
        if start_dt is not None:
            raise NotImplementedError()
        return self._df.copy()

    def set_df(self, value):
        if not isinstance(value, pd.DataFrame):
            raise EPWError("df must be a DataFrame")
        assert_index_equal(value.index, self._df.index)
        assert_index_equal(value.columns, self._df.columns)


class EPWHeader:
    def __init__(self, header_s):
        self._header_l2 = []
        for line_s in header_s.strip().split("\n"):
            self._header_l2.append([cell.strip() for cell in line_s.split(",")])
        # check
        if len(self._data_periods_l) != 7:
            raise EPWError("'DATA PERIODS' row must have 7 cells.")
        if self._data_periods_l[0] != "DATA PERIODS":
            raise EPWError("Last line of header must be 'DATA PERIODS'.")
        if self._data_periods_l[1] != "1":
            raise NotImplementedError("Can only manage epws with one data period.")
        if self._data_periods_l[2] != "1":
            raise NotImplementedError("Can only manage hourly epws.")

    def to_str(self):
        return "\n".join([",".join(row) for row in self._header_l2])

    @property
    def _data_periods_l(self):
        return self._header_l2[-1]

    @property
    def start(self):
        """
        (month, day)
        """
        return self._data_periods_l[5].split(",").map(int)

    @start.setter
    def start(self, value):
        self._data_periods_l[5] = "%s/%s" % value

    @property
    def end(self):
        """
        (month, day)
        """
        return self._data_periods_l[6].split(",").map(int)

    @end.setter
    def end(self, value):
        self._data_periods_l[6] = "%s/%s" % value

    @property
    def freq(self):
        return {"1": "H"}[self._data_periods_l[2]]


def parse_epw(file_like, encoding=None, logger_name=None):
    header_s = ""

    # header
    for line_s in file_like:
        header_s += line_s
        if re.match("^DATA PERIODS", line_s) is not None:
            break
    header = EPWHeader(header_s)

    # data
    df = pd.read_csv(file_like, header=None, low_memory=False)
    df.columns = EPW_COLUMNS[:len(df.columns)]
    df.index = pd.MultiIndex.from_arrays([df[c] for c in df.columns[:5]])
    for c in df.columns[:5].tolist():
        del df[c]

    return df, header


