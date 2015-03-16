import os

import pandas as pd

from oplus.configuration import CONFIG

default_logger_name = __name__ if CONFIG.logger_name is None else CONFIG.logger_name


class EIOError(Exception):
    pass


class EndOfReportError(EIOError):
    pass


class EIO:
    def __init__(self, path, logger_name=None, encoding=None):
        if not os.path.isfile(path):
            raise EIOError("No file at given path: '%s'." % path)
        self._path = path
        self._logger_name = logger_name
        self._encoding = encoding

        self._dfs_d = parse_eio(self._path, encoding=encoding)

    def df(self, table_ref):
        return self._dfs_d[table_ref]

    def get_value(self, table_ref, column_name_or_i, filter_column_name_or_i, filter_criterion):
        if not table_ref in self._dfs_d:
            raise EIOError("Unknown table_ref: '%s'." % table_ref)
        df = self._dfs_d[table_ref]

        # find column indexes
        column_i = self._get_column_index(df, column_name_or_i)
        filter_column_i = self._get_column_index(df, filter_column_name_or_i)

        answer_df = df[df[df.columns[filter_column_i]] == filter_criterion]
        if len(answer_df) == 0:
            raise EIOError("Filter did not return any values.")
        if len(answer_df) > 1:
            raise EIOError("Filter returned more than one value.")
        return answer_df.iloc[0, column_i]

    @staticmethod
    def _get_column_index(df, column_name_or_i):
        if isinstance(column_name_or_i, int) or isinstance(column_name_or_i, float):
            return column_name_or_i
        if not column_name_or_i in df.columns:
            raise EIOError("Unknown column '%s' for table '%s'." % (column_name_or_i, df.index.name))
        return df.columns.tolist().index(column_name_or_i)


def parse_eio(path, encoding=None):
    headers_l2 = [["<Program Version>", "Program Version ID", "YMD"]]
    content_d = {}  # {ref: data_l2, ...}
    content_header_d = {}  # {name: header_row, ...}

    # _header_ref_pattern_ = "^([^<.]*)<([^>.]*)>(.*)$"

    with open(path, encoding=CONFIG.encoding if encoding is None else encoding) as f:
        for line_s in f:
            if line_s == "End of Data":
                break
            line_s = line_s.strip().strip(",")
            line_l = []
            for c in line_s.split(","):
                c = c.strip()
                try:
                    c = float(c)
                except ValueError:
                    pass
                line_l.append(c)
            if line_s[0][0] == "!":  # header
                headers_l2.append([line_l[0][1:].strip()] + line_l[1:])
            else:  # content
                ref = line_l[0]
                if not ref in content_d:
                    content_d[ref] = []
                content_d[ref].append(line_l[1:])
                # find header if necessary
                if not ref in content_header_d:
                    for i in range(len(headers_l2)-1, -1, -1):
                        if ref.lower() in headers_l2[i][0].lower():
                            content_header_d[ref] = i
                            break

    # prepare data for dataframes
    dfs_d = {}
    for ref, data in content_d.items():
        header_i = content_header_d.get(ref)
        if header_i is None:  # header not found
            header_columns = []
        else:
            header_columns = headers_l2[header_i][1:]
            if len(header_columns) == 1 and ("Months From Jan to Dec" in header_columns[0]):
                header_columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        # prepare columns and data
        data_columns_nb = max([len(r) for r in data])
        columns_nb = max(data_columns_nb, len(header_columns))

        _columns = header_columns + ["c%i" % i for i in range(columns_nb-len(header_columns))]
        _data = []
        for r in data:
            _data.append(r + [None]*(columns_nb-len(r)))

        dfs_d[ref] = pd.DataFrame(data=_data, columns=_columns)
        dfs_d[ref].index.name = ref

    return dfs_d
