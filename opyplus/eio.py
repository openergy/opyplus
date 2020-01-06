"""module to handle EnergyPlus .eio files."""

import os

import pandas as pd

from opyplus.conf import CONF


class Eio:
    """
    Class describing a .eio file.

    Parameters
    ----------
    path: str
        Path of the .eio file
    """

    def __init__(self, path):
        if not os.path.isfile(path):
            raise FileNotFoundError("No file at given path: '%s'." % path)
        self._path = path

        self._tables_d = parse_eio(self._path)  # { lower_ref: EioTable(), ...

    # -------------------------------------- public api ----------------------------------------------------------------
    def get_table_refs(self):
        """
        Get eio table references.

        Returns
        -------
        typing.Iterator[str]
            Eio table references
        """
        return self._tables_d.keys()

    def get_df(self, table_ref):
        """
        Get the content of a table of the .eio file as a dataframe.

        Parameters
        ----------
        table_ref: str
            table reference

        Returns
        -------
        pandas.DataFrame
        """
        return self._tables_d[table_ref.lower()].get_df()

    def get_value(self, table_ref, column_name_or_i, filter_column_name_or_i, filter_criterion):
        """
        Get first occurrence of value of filter column matching filter criterion.

        Parameters
        ----------
        table_ref: str
        column_name_or_i: str or int
        filter_column_name_or_i: str or int
        filter_criterion: str
        """
        lower_ref = table_ref.lower()
        if lower_ref not in self._tables_d:
            raise KeyError("Unknown table_ref: '%s'." % table_ref)
        return self._tables_d[lower_ref].get_value(column_name_or_i, filter_column_name_or_i, filter_criterion)


def parse_eio(path):
    """
    Parse an eio file.

    Parameters
    ----------
    path: str
        eio file path

    Returns
    -------
    typing.Dict[str, EioTable]
    """
    headers_l2 = [["<Program Version>", "Program Version ID", "YMD"]]
    content_d = {}  # {ref: data_l2, ...}
    content_header_d = {}  # {ref (istr(): header_row, ...}

    # _header_ref_pattern_ = "^([^<.]*)<([^>.]*)>(.*)$"

    with open(path, encoding=CONF.encoding) as f:
        for line_s in f:
            if line_s == "End of Data":
                break
            line_s = line_s.strip().strip(",")
            line_l = [c.strip() for c in line_s.split(",")]
            if line_s[0][0] == "!":  # header
                headers_l2.append([line_l[0][1:].strip()] + line_l[1:])
            else:  # content
                ref = line_l[0]
                if ref not in content_d:
                    content_d[ref] = []
                content_d[ref].append(line_l[1:])
                # find header if necessary
                if ref not in content_header_d:
                    for i in range(len(headers_l2)-1, -1, -1):
                        if ref in headers_l2[i][0]:
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

        tables_d[ref.lower()] = EioTable(ref, _columns, _data)

    return tables_d


class EioTable:
    """
    Class describing a table of a .eio file.

    Parameters
    ----------
    ref: str
    columns: list of str
    """

    def __init__(self, ref, columns, data):
        # Store dataframe info without parsing types (otherwise dtypes are changed even if dtyp='object' is asked...)
        # check
        col_len = len(columns)
        for i, r in enumerate(data):
            if len(r) != col_len:
                raise RuntimeError("Wrong number of columns in row %i of table %s." % (i, ref))

        self._ref = ref
        self._columns = columns
        self._data = data

    def _get_column_index(self, column_name_or_i):
        if isinstance(column_name_or_i, int) or isinstance(column_name_or_i, float):
            return column_name_or_i
        if column_name_or_i not in self._columns:
            raise KeyError("Unknown column '%s' for table '%s'." % (column_name_or_i, self._ref))
        return self._columns.index(column_name_or_i)

    def get_df(self):
        """
        Get table data as a data frame.

        Returns
        -------
        pandas.DataFrame
        """
        _df = pd.DataFrame(data=self._data, columns=self._columns, dtype="object")
        _df.name = self._ref
        return _df

    def get_value(self, column_name_or_i, filter_column_name_or_i, filter_criterion):
        """
        Return first occurrence of value of filter column matching filter criterion.

        Parameters
        ----------
        column_name_or_i: str or int
        filter_column_name_or_i: str or int
        filter_criterion: str
        """
        # find column indexes
        column_i = self._get_column_index(column_name_or_i)
        filter_column_i = self._get_column_index(filter_column_name_or_i)

        filter_fct = {
            float: lambda x: float(x) == filter_criterion,
            int: lambda x: int(x) == filter_criterion,
            str: lambda x: x.lower() == filter_criterion.lower()
        }[type(filter_criterion)]

        for row_i, row in enumerate(self._data):
            if filter_fct(row[filter_column_i]):
                break
        else:
            raise ValueError("Filter did not return any values.")

        return self._data[row_i][column_i]
