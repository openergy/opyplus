import codecs
import logging

import pandas as pd

from oplus.configuration import CONFIG



default_logger_name = __name__ if CONFIG.logger_name is None else CONFIG.logger_name

# todo: recode


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


    # def filter(self, **kwargs):
    #     filter_a = None
    #     for k, v in kwargs:
    #         if filter_a is None:
    #             filter_a = self.df[k] == v
    #         else:
    #             filter_a = np.logical_and(filter_a, self.df[k] == v.upper())
    #     df = self.df[filter_a]
    #     return Table(self.ref, df, self._link_ref)
    #
    # def get(self, **kwargs):
    #     table = self.filter(**kwargs)
    #     if len(table.df) == 0:
    #         raise DoesNotExist()
    #     if len(table.df) > 1:
    #         raise MultipleObjectsReturned()
    #
    #     d = {}
    #     for c in table.df.columns:
    #         d[c] = table.df[c].iloc[0]
    #
    #     return d


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


        # self._maintable_ref = None
        # self._subtables_refs_l = []
        #
        # self._maintable_l2 = []  # maintable_l2
        # self._subtables_l2_l_l = []  # [[t11_l2, t12_l2, ...], [t21_l2, t21_l2, ...], ...]


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
        # if table_num == 0:  # main table
        #     self.data_l2_l[table_num].append(row_l[1:])
        # else:  # child table
        #     self.data_l2_l[table_num].append(row_l[1:] + [len(self.data_l2_l[0])-1])
        # if self._maintable_ref is None:
        #     self._maintable_ref = ref
        # elif ref != self._maintable_ref and ref not in self._subtables_refs_l:
        #     self._subtables_refs_l.append(ref)
        #
        # # append row
        # if ref == self._maintable_ref:  # main table row
        #     self._maintable_l2.append(row_l[1:])
        #     self._subtables_l2_l_l.append([])
        # else:  # sub table row
        #     # table index
        #     subtable_index = self._subtables_refs_l.index(ref)
        #     # we create all missing tables
        #     current_subtable_l2_l = self._subtables_l2_l_l[-1]
        #     while len(current_subtable_l2_l) < subtable_index+1:
        #         current_subtable_l2_l.append([])
        #     current_subtable_l2_l[subtable_index].append(row_l[1:])

    def get_tables_l(self):
        """transforms data_l2 in dataframes, create tables and return them"""
        tables_l = []
        for table_num, data_l2 in enumerate(self.data_l2_l):
            table_ref = self.refs_l[table_num]
            columns = self._get_columns(table_ref)
            if columns is None:
                logging.getLogger(default_logger_name).error("Error while parsing table '%s'. Left aside." % table_ref)
                continue
            if table_num != 0:  # child table, add link column
                columns = [Table.fk_col_name(self.refs_l[0])] + columns
            df = pd.DataFrame(columns=columns, data=data_l2)
            tables_l.append(special_tables_classes_d.get(table_ref, Table)(table_ref, df, self.refs_l[0]))
        return tables_l




        # # main table - no link
        # tables_df_l = [Table(pd.DataFrame(columns=self._get_columns(self._maintable_ref), data=self._maintable_l2))]
        #
        # subtables_l2_d = {}
        # for link_id, table_l2_l in enumerate(self._subtables_l2_l_l):
        #     for subtable_key, table_l2 in enumerate(table_l2_l):
        #         if not subtable_key in subtables_l2_d:
        #             subtables_l2_d[subtable_key] = []
        #         subtables_l2_d[subtable_key].append(
        #
        # pd.DataFrame(columns=self._get_columns(self._subtables_refs_l[index]), data=table_l2))
        #
        #
        # for ref in [self._maintable_ref] + self._subtables_refs_l:
        #     if ref in report_refs_l:
        #
        #         print("double: %s" % ref)


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
    def __init__(self, path):
        self.path = path
        self.tables_d = {}
        self._parse()

    def _parse(self):
        # load data
        f = codecs.open(self.path, encoding="latin-1")
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
                        if table.ref in self.tables_d:
                            raise EIOError("table_ref already in self.tables_d: '%s'" % table.ref)
                        self.tables_d[table.ref] = table

                    # create new report
                    current_report = Report()
                current_report.add_header_row(row)
            else:  # body
                if current_report is None:  # new report
                    current_report = Report()
                current_report.add_body_row(row)

    def __call__(self, table_ref, **kwargs):
        if len(kwargs) != 0:
            raise NotImplementedError()
        table = self.tables_d[table_ref]
        return table



if __name__ == "__main__":
    # test antoine
    my_eio = EIO(r"C:\Users\Geoffroy\Google Drive\Dossiers employes\LEFORT Antoine\Design Builder\Villiers_Rx_1.eio")
    zone_sizing_tbl = my_eio("Zone Sizing Information")

    df = zone_sizing_tbl.df.copy()
    df.index = df["Zone Name"]
    print(df[df["Load Type"] == "Cooling"]["Calc Des Load {W}"])



