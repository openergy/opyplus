import os
import codecs
import logging

import pandas as pd

from oplus.configuration import CONFIG



default_logger_name = __name__ if CONFIG.logger_name is None else CONFIG.logger_name

# todo: refactor
# todo: manage all eio without skipping logging errors


class EIOError(Exception):
    pass


class DoesNotExist(EIOError):
    pass


class MultipleObjectsReturned(EIOError):
    pass


header_body_links_d = {  # when header does is not exactly used in body
    "Zone/Shading Surfaces": ["Zone_Surfaces"],
    "HeatTransfer/Shading/Frame/Divider_Surface": ["HeatTransfer_Surface"],

}

report_refs_l = []


class Table:
    @staticmethod
    def df_to_dict_l(df):
        d_l = []
        for row_num, se in df.iterrows():
            d = {}
            for c in se.index:
                d[c] = se[c]
            d_l.append(d)
        return d_l

    @classmethod
    def df_to_unique_dict(cls, df):
        d_l = cls.df_to_dict_l(df)
        if len(d_l) < 1:
            raise DoesNotExist()
        if len(d_l) > 1:
            raise MultipleObjectsReturned(str(d_l))
        return d_l[0]

    @staticmethod
    def fk_col_name(foreign_table_ref):
        return "LINK:%s" % foreign_table_ref

    def __init__(self, ref, df, link_ref=None):
        self.ref = ref
        self.df = df
        self._link_ref = link_ref


class HeatTransferSurfaceTable(Table):
    def get(self, surface_name):
        df = self.df[self.df["Surface Name"] == surface_name.upper()]
        d = self.df_to_unique_dict(df)
        return d


class WindowConstructionTable(Table):
    def get(self, construction_name):
        df = self.df[self.df["Construction Name"] == construction_name.upper()]
        d = self.df_to_unique_dict(df)
        return d


class ZoneAirflowStatsTable(Table):
    def get_if_exists(self, zone_name):
        df = self.df[self.df[2] == zone_name.upper()]
        # we put '2' instead of 'Zone Name' because header is not set (header_ref != body_ref)
        if len(df) == 0:
            return None
        d = self.df_to_unique_dict(df)
        return d


class ZoneInformationTable(Table):
    def get(self, zone_name):
        df = self.df[self.df["Zone Name"] == zone_name.upper()]
        d = self.df_to_unique_dict(df)
        return d


special_tables_classes_d = {
    "HeatTransfer_Surface": HeatTransferSurfaceTable,
    "WindowConstruction": WindowConstructionTable,
    "ZoneInfiltration Airflow Stats": ZoneAirflowStatsTable,
    "ZoneVentilation Airflow Stats": ZoneAirflowStatsTable,
    "Zone Information": ZoneInformationTable}


class Report:
    def __init__(self):
        self.defining_header = True

        # headers
        self._headers_d = {}

        # refs management
        self.refs_l = []
        self.data_l2_l = []

    @property
    def ref(self):
        return self.refs_l[0]

    def add_header_row(self, row):
        row = self._prepare_row(row)
        row_l = [val.strip() for val in row[1:].split(",")]
        self._headers_d[row_l[0][1:-1]] = row_l[1:]

    def add_body_row(self, row):
        row = self._prepare_row(row)
        self.defining_header = False
        # parse
        row_l = [val.strip() for val in row.split(",")]

        # manage refs
        ref = row_l[0]
        if not ref in self.refs_l:
            self.refs_l.append(ref)

        table_num = self.refs_l.index(ref)
        while len(self.data_l2_l) < table_num + 1:
            self.data_l2_l.append([])

        # append row at beginning. If not main table, we add a new column pointing on main table current row_num
        row_l = ([len(self.data_l2_l[0])-1] if table_num != 0 else []) + row_l[1:]
        self.data_l2_l[table_num].append(row_l)

    def get_tables_l(self):
        """transforms data_l2 in dataframes, create tables and return them"""
        tables_l = []
        for table_num, data_l2 in enumerate(self.data_l2_l):
            table_ref = self.refs_l[table_num]
            columns = self._get_columns(table_ref)
            if columns is None:
                # todo: user logger given in EIO
                logging.getLogger(default_logger_name).error("Error while parsing table '%s' (columns is None). "
                                                             "Left aside." % table_ref)
                continue
            if table_num != 0:  # child table, add link column
                columns = [Table.fk_col_name(self.refs_l[0])] + columns
            try:
                df = pd.DataFrame(columns=columns, data=data_l2)
            except AssertionError:
                logging.getLogger(default_logger_name).error("Error while parsing table '%s' "
                                                             "(while dataframe creation).  Left aside." % table_ref)
                continue
            tables_l.append(special_tables_classes_d.get(table_ref, Table)(table_ref, df, self.refs_l[0]))
        return tables_l

    def _get_columns(self, body_ref):
        # in header
        raw_columns = None
        if body_ref in self._headers_d:
            raw_columns = self._headers_d[body_ref]
        for header_ref in self._headers_d:
            if header_ref in header_body_links_d:
                if body_ref in header_body_links_d[header_ref]:
                    raw_columns = self._headers_d[header_ref]
                    break

        if raw_columns is None:
            return None
        if len(raw_columns) == 1 and "Months From Jan to Dec" in raw_columns[0]:
            return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return raw_columns

    def _prepare_row(self, row):
        return row.strip().rstrip(",")


class EIO:
    def __init__(self, path, logger_name=None, encoding=None):
        if not os.path.isfile(path):
            raise EIOError("No file at given path: '%s'." % path)
        self._path = path
        self._logger_name = logger_name
        self._encoding = encoding

        self._tables_d = self._parse()

    def _parse(self):
        tables_d = {}
        # load data
        with open(self._path, encoding=self._encoding) as f:
            current_report = None
            for row in f:
                if row == "End of Data":
                    break
                if len(row) == 0:
                    continue
                if row[0] == "!":  # header
                    if current_report is None:
                        current_report = Report()
                    if not current_report.defining_header:  # new report
                        # save
                        tables_l = current_report.get_tables_l()
                        for table in tables_l:
                            if table.ref in tables_d:
                                raise EIOError("table_ref already in self.tables_d: '%s'" % table.ref)
                            tables_d[table.ref] = table

                        # create new report
                        current_report = Report()
                    current_report.add_header_row(row)
                else:  # body
                    if current_report is None:  # new report
                        current_report = Report()
                    current_report.add_body_row(row)
            return tables_d

    def __call__(self, table_ref, **kwargs):
        if len(kwargs) != 0:
            raise NotImplementedError()
        table = self._tables_d[table_ref]
        return table



if __name__ == "__main__":
    # test antoine
    my_eio = EIO(r"C:\Users\Geoffroy\Google Drive\Dossiers employes\LEFORT Antoine\Design Builder\Villiers_Rx_1.eio")
    zone_sizing_tbl = my_eio("Zone Sizing Information")

    df = zone_sizing_tbl.df.copy()
    df.index = df["Zone Name"]
    print(df[df["Load Type"] == "Cooling"]["Calc Des Load {W}"])



