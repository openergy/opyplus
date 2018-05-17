import os

import pandas as pd

from oplus.configuration import CONF


class OutputTable:
    def __init__(self, path, logger_name=None, encoding=None):
        assert os.path.isfile(path), "No file at given path: '%s'." % path
        self._path = path
        self._logger_name = logger_name
        self._encoding = encoding

        self._reports_d = self._parse()  # {report_name: {table_name: df, ...}, ...}

    def _parse(self):
        # constants
        _name_ = "name"
        _columns_ = "columns"
        _values_ = "values"
        _index_ = "index"

        # variables
        raw_reports_d = {}  # {report_name: [tables_d, ...], ...}
        current_raw_tables_l = None
        current_raw_table_d = None  # {"name": "name", "columns": "columns", values: [[v1, ...], ...]}
        columns_nb = None

        def to_float_if_possible(s):
            try:
                return float(s)
            except ValueError:
                if s.strip() == "":
                    return None
                else:
                    return s

        # loop
        with open(self._path, "r", encoding=CONF.encoding if self._encoding is None else self._encoding) as f:
            while True:
                # next line
                try:
                    line_s = next(f).strip()
                except StopIteration:
                    break

                # use everything except table names and values
                if line_s[:6] == "REPORT":
                    # find report name
                    report_name = line_s.split(",")[1].strip()
                    # create new report
                    current_raw_tables_l = []
                    raw_reports_d[report_name] = current_raw_tables_l
                    # create empty current_raw_table_d to initialize
                    current_raw_table_d = {_index_: [], _values_: []}
                    # skip two next lines
                    for i in range(2):
                        next(f)
                    continue
                elif current_raw_tables_l is None:
                    # first table not reached yet, nothing to do
                    continue
                elif line_s[:5] == "Note ":  # end notes
                    break

                # parse tables
                if line_s.strip() == "":
                    if _columns_ in current_raw_table_d:
                        # end of data, we create a new current_raw_table_d
                        current_raw_table_d = {_index_: [], _values_: []}
                elif _name_ not in current_raw_table_d:
                    # we know this table exists (we are not in end of file), so we name and append
                    current_raw_table_d[_name_] = line_s
                    current_raw_tables_l.append(current_raw_table_d)
                elif _columns_ not in current_raw_table_d:
                    columns_l = line_s.split(",")[2:]
                    current_raw_table_d[_columns_] = columns_l
                    columns_nb = len(columns_l)
                else:
                    line_l = line_s.split(",")
                    if len(line_l) <= 1:  # comments sometimes follow a table, without a whitespace
                        continue
                    current_raw_table_d[_index_].append(",".join(line_l[1:-columns_nb]))
                    current_raw_table_d[_values_].append([to_float_if_possible(s) for s in line_l[-columns_nb:]])

        # create dataframes
        reports_d = {}
        for report_name, raw_tables_l in raw_reports_d.items():
            tables_d = {}
            for raw_table_d in raw_tables_l:
                tables_d[raw_table_d[_name_]] = pd.DataFrame(data=raw_table_d[_values_], index=raw_table_d[_index_],
                                                             columns=raw_table_d[_columns_])
            reports_d[report_name] = tables_d

        return reports_d

    def get_table(self, table_name, report_name=None):
        if report_name is None:
            for rp_name, tables_d in self._reports_d.items():
                if table_name in tables_d:
                    return tables_d[table_name]
            raise KeyError("Table name '%s' not found." % table_name)

        if report_name not in self._reports_d:
            raise KeyError("Report name '%s' not found." % report_name)
        tables_d = self._reports_d[report_name]

        if table_name not in tables_d:
            raise KeyError("Table name '%s' not found in report '%s'." % (table_name, report_name))
        return tables_d[table_name]
