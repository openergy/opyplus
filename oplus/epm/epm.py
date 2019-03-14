import os
import collections

from ..configuration import CONF
from .idd import Idd
from .table import Table
from .record import Record
from .relations_manager import RelationsManager
from .idf_parse import parse_idf
from .util import json_data_to_json


class Epm:
    """
    Energyplus model
    """
    _dev_record_cls = Record  # for subclassing
    _dev_table_cls = Table  # for subclassing
    _dev_idd_cls = Idd  # for subclassing

    def __init__(self, idf_buffer_or_path=None, idd_or_buffer_or_path=None, comment=None, encoding=None):
        # set variables
        self._encoding = CONF.encoding if encoding is None else encoding
        self._path = None
        self._dev_idd = (
            idd_or_buffer_or_path if isinstance(idd_or_buffer_or_path, Idd) else
            self._dev_idd_cls(idd_or_buffer_or_path, encoding=encoding)
        )
        self._tables = collections.OrderedDict(sorted([  # {lower_ref: table, ...}
            (table_descriptor.table_ref.lower(), Table(table_descriptor, self))
            for table_descriptor in self._dev_idd.table_descriptors.values()
        ]))
        self._dev_relations_manager = RelationsManager(self)
        self._comment = "" if comment is None else str(comment)

        # parse if relevant
        if idf_buffer_or_path is not None:
            if isinstance(idf_buffer_or_path, str):
                if not os.path.isfile(idf_buffer_or_path):
                    raise FileNotFoundError(f"no idf found at given path: {idf_buffer_or_path}")
                self._path = idf_buffer_or_path
                buffer = open(idf_buffer_or_path, encoding=self._encoding)
            else:
                buffer = idf_buffer_or_path

            # raw parse and parse
            with buffer as f:
                json_data = parse_idf(f)

            # populate
            self._dev_populate_from_json_data(json_data)

    def _dev_populate_from_json_data(self, json_data):
        # manage comment if any
        comment = json_data.pop("_comment", None)
        if comment is not None:
            self._comment = comment

        # manage records
        added_records = []
        for table_ref, json_data_records in json_data.items():
            # find table
            table = getattr(self, table_ref)

            # create record (inert)
            records = table._dev_add_inert(json_data_records)

            # add records (inert)
            added_records.extend(records)

        # activate hooks
        for r in added_records:
            r._dev_activate_hooks()

        # activate links
        for r in added_records:
            r._dev_activate_links()

    # --------------------------------------------- public api ---------------------------------------------------------
    # python magic
    def __repr__(self):
        return "<Epm>"

    def __str__(self):
        s = "Epm\n"

        for table in self._tables.values():
            records_nb = len(table)
            if records_nb == 0:
                continue
            plural = "" if records_nb == 1 else "s"
            s += f"  {table.get_name()}: {records_nb} record{plural}\n"

        return s

    def __eq__(self, other):
        return self.to_json_data() != other.to_json_data()

    def __dir__(self):
        return [t.get_ref() for t in self._tables.values()] + list(self.__dict__)

    def __getattr__(self, item):
        try:
            return self._tables[item.lower()]
        except KeyError:
            raise AttributeError(f"No table with reference '{item}'.")

    def __iter__(self):
        return iter(self._tables.values())

    # get info
    def get_comment(self):
        return self._comment

    def get_info(self):
        return "Energy plus model\n" + "\n".join(
            f"  {table._dev_descriptor.table_ref}" for table in self._tables.values()
        )

    def set_defaults(self):
        for table in self._tables.values():
            for r in table:
                r.set_defaults()

    # ------------------------------------------- load -----------------------------------------------------------------
    @classmethod
    def from_json_data(cls, json_data):
        idf = cls()
        idf._dev_populate_from_json_data(json_data)
        return idf

    @classmethod
    def from_idf(cls, buffer_or_path, idd_or_buffer_or_path=None, comment=None, encoding=None):
        return cls(
            idf_buffer_or_path=buffer_or_path,
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            comment=comment,
            encoding=encoding
        )

    # ----------------------------------------- export -----------------------------------------------------------------
    def to_json_data(self):
        return collections.OrderedDict((t.get_ref(), t.to_json_data()) for t in self._tables.values())

    def to_json(self, buffer_or_path=None, indent=2):
        # todo: manage copyright and comment
        return json_data_to_json(
            self.to_json_data(),
            buffer_or_path=buffer_or_path,
            indent=indent
        )
        
    def to_idf(self):
        # todo: manage copyright and comment
        formatted_records = []
        for table_ref, table in self._tables.items():  # self._tables is already sorted
            formatted_records.extend([r.to_idf() for r in sorted(table)])
        return "\n\n".join(formatted_records)
