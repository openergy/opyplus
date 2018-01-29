import os

import pandas as pd

from oplus.configuration import CONF


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

        self._tables_d = parse_eio(self._path, encoding=encoding)

    @property
    def table_refs(self):
        return self._tables_d.keys()

    def df(self, table_ref):
        return self._tables_d[table_ref].df

    def get_value(self, table_ref, column_name_or_i, filter_column_name_or_i, filter_criterion):
        if not table_ref in self._tables_d:
            raise EIOError("Unknown table_ref: '%s'." % table_ref)
        return self._tables_d[table_ref].get_value(column_name_or_i, filter_column_name_or_i, filter_criterion)


def parse_eio(path, encoding=None):
    headers_l2 = [["<Program Version>", "Program Version ID", "YMD"]]
    content_d = {}  # {ref: data_l2, ...}
    content_header_d = {}  # {name: header_row, ...}

    # _header_ref_pattern_ = "^([^<.]*)<([^>.]*)>(.*)$"

    with open(path, encoding=CONF.encoding if encoding is None else encoding) as f:
        for line_s in f:
            if line_s == "End of Data":
                break
            line_s = line_s.strip().strip(",")
            line_l = [c.strip() for c in line_s.split(",")]
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
    tables_d = {}
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

        tables_d[ref] = EIOTable(ref, _columns, _data)

    return tables_d


class EIOTable:
    def __init__(self, ref, columns, data):
        """
        Stores dataframe info without parsing types (otherwise dtypes are changed even if dtyp='object' is asked...)
        """
        # check
        col_len = len(columns)
        for i, r in enumerate(data):
            if len(r) != col_len:
                raise EIOError("Wrong number of columns in row %i of table %s." % (i, ref))

        self._ref = ref
        self._columns = columns
        self._data = data

    @property
    def df(self):
        _df = pd.DataFrame(data=self._data, columns=self._columns, dtype="object")
        _df.name = self._ref
        return _df

    def get_value(self, column_name_or_i, filter_column_name_or_i, filter_criterion):
        """
        Returns first occurrence of value of filter column matching filter criterion.
        """
        # find column indexes
        column_i = self._get_column_index(column_name_or_i)
        filter_column_i = self._get_column_index(filter_column_name_or_i)

        filter_fct = {
            float: lambda x: float(x) == filter_criterion,
            int: lambda x: int(x) == filter_criterion,
            str: lambda x: str(x).lower() == filter_criterion.lower()
        }[type(filter_criterion)]

        for row_i, row in enumerate(self._data):
            if filter_fct(row[filter_column_i]):
                break
        else:
            raise EIOError("Filter did not return any values.")

        return self._data[row_i][column_i]

    def _get_column_index(self, column_name_or_i):
        if isinstance(column_name_or_i, int) or isinstance(column_name_or_i, float):
            return column_name_or_i
        if not column_name_or_i in self._columns:
            raise EIOError("Unknown column '%s' for table '%s'." % (column_name_or_i, df.index.name))
        return self._columns.index(column_name_or_i)