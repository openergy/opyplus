import os
import collections
import textwrap
import json
import contextlib

from ..util import get_multi_line_copyright_message, to_buffer

from .idd import Idd
from .table import Table
from .record import Record
from .relations_manager import RelationsManager
from .idf_parse import parse_idf
from .util import json_data_to_json, multi_mode_write


class Epm:
    """
    Energyplus model
    """
    _dev_record_cls = Record  # for subclassing
    _dev_table_cls = Table  # for subclassing
    _dev_idd_cls = Idd  # for subclassing

    def __init__(self, idd_or_buffer_or_path=None, check_required=True):
        """
        Parameters
        ----------
        idd_or_buffer_or_path
        check_required
        """
        self._dev_idd = (
            idd_or_buffer_or_path if isinstance(idd_or_buffer_or_path, Idd) else
            self._dev_idd_cls(idd_or_buffer_or_path)
        )
        # !! relations manager must be defined before table creation because table creation will trigger
        # hook registering
        self._dev_relations_manager = RelationsManager(self)

        self._tables = collections.OrderedDict(sorted([  # {lower_ref: table, ...}
            (table_descriptor.table_ref.lower(), Table(table_descriptor, self))
            for table_descriptor in self._dev_idd.table_descriptors.values()
        ]))

        self._dev_check_required = check_required
        self._dev_current_model_file_path = None  # read only except from epm context manager
        self._comment = ""

    # ------------------------------------------ private ---------------------------------------------------------------
    @classmethod
    def _create_from_buffer_or_path(
            cls,
            parse_fct,
            buffer_or_path,
            idd_or_buffer_or_path=None,
            check_required=True,
            model_file_path=None
    ):
        # prepare buffer
        _source_file_path, buffer = to_buffer(buffer_or_path)

        # manage source file path
        model_file_path = _source_file_path if model_file_path is None else _source_file_path

        # create json data
        with buffer as f:
            json_data = parse_fct(f)

        # create and return epm
        return cls.from_json_data(
            json_data,
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required,
            model_file_path=model_file_path
        )

    # ------------------------------------------ dev api ---------------------------------------------------------------
    @contextlib.contextmanager
    def _dev_set_current_model_file_path(self, model_file_path):
        if model_file_path is not None:
            # ensure absolute and store
            self._dev_current_model_file_path = model_file_path
        try:
            yield
        finally:
            self._dev_current_model_file_path = None

    def _dev_populate_from_json_data(self, json_data):
        """
        workflow
        --------
        (methods belonging to create/update/delete framework:
            epm._dev_populate_from_json_data, table.batch_add, record.update, queryset.delete, record.delete)
        1. add inert
            * data is checked
            * old links are unregistered
            * record is stored in table (=> pk uniqueness is checked)
        2. activate hooks
        3. activate links
        """
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

    def __getattr__(self, item):
        try:
            return self._tables[item.lower()]
        except KeyError:
            raise AttributeError(f"No table with reference '{item}'.")

    def __eq__(self, other):
        return self.to_json_data() != other.to_json_data()

    def __iter__(self):
        return iter(self._tables.values())

    def __dir__(self):
        return [t.get_ref() for t in self._tables.values()] + list(self.__dict__)

    # get info
    def get_comment(self):
        return self._comment

    # get idd info
    def get_info(self):
        return "Energy plus model\n" + "\n".join(
            f"  {table._dev_descriptor.table_ref}" for table in self._tables.values()
        )

    def get_external_files(self):
        external_files = []
        for table in self._tables.values():
            for r in table:
                external_files.extend([ef for ef in r.get_external_files()])
        return external_files

    # construct
    def set_comment(self, comment):
        self._comment = str(comment)

    def set_defaults(self):
        for table in self._tables.values():
            for r in table:
                r.set_defaults()

    def gather_external_files(self, target_dir_path, copy=True):
        # collect external files
        external_files = self.get_external_files()

        # leave if no external files
        if len(external_files) == 0:
            return

        # check that all external files exists
        for ef in external_files:
            ef.check_file_exists()

        # prepare directory (or check existing)
        if not os.path.exists(target_dir_path):
            os.mkdir(target_dir_path)
        elif not os.path.isdir(target_dir_path):
            raise NotADirectoryError(f"given dir_path is not a directory: {target_dir_path}")

        # copy or move files
        mode = "copy" if copy else "move"
        raise_if_not_found = True if copy else False
        # since file may already have been moved, and since we checked that all files existed, we don't raise
        # if file is not found
        for ef in external_files:
            ef.transfer(target_dir_path, mode=mode, raise_if_not_found=raise_if_not_found)

    # ------------------------------------------- load -----------------------------------------------------------------
    @classmethod
    def from_json_data(cls, json_data, idd_or_buffer_or_path=None, check_required=True, model_file_path=None):
        epm = cls(
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required
        )

        with epm._dev_set_current_model_file_path(model_file_path):
            epm._dev_populate_from_json_data(json_data)
        return epm

    @classmethod
    def from_idf(cls, buffer_or_path, idd_or_buffer_or_path=None, check_required=True, model_file_path=None):
        return cls._create_from_buffer_or_path(
            parse_idf,
            buffer_or_path,
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required,
            model_file_path=model_file_path
        )

    @classmethod
    def from_json(cls, buffer_or_path, idd_or_buffer_or_path=None, check_required=True, source_file_path=None):
        return cls._create_from_buffer_or_path(
            json.load,
            buffer_or_path,
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required,
            model_file_path=source_file_path
        )

    # ----------------------------------------- export -----------------------------------------------------------------
    def to_json_data(self, external_files_mode=None, model_file_path=None):
        """
        Parameters
        ----------
        external_files_mode: str, default 'relative'
            'relative', 'absolute'
        model_file_path
        """
        # create data
        with self._dev_set_current_model_file_path(model_file_path):
            d = collections.OrderedDict(
                (t.get_ref(), t.to_json_data(external_files_mode=external_files_mode)) for t in self._tables.values()
            )
            d["_comment"] = self._comment
            d.move_to_end("_comment", last=False)
            return d

    def to_json(self, buffer_or_path=None, indent=2, external_files_mode=None, model_file_path=None):
        # set model file path if not given and target path is given
        if (model_file_path is None) and isinstance(buffer_or_path, str):
            model_file_path = buffer_or_path

        # return json
        return json_data_to_json(
            self.to_json_data(
                external_files_mode=external_files_mode,
                model_file_path=model_file_path
            ),
            buffer_or_path=buffer_or_path,
            indent=indent
        )
        
    def to_idf(self, buffer_or_path=None, external_files_mode=None, model_file_path=None):
        # set model file path if not given and target path is given
        if (model_file_path is None) and isinstance(buffer_or_path, str):
            model_file_path = buffer_or_path

        # prepare comment
        comment = get_multi_line_copyright_message()
        if self._comment != "":
            comment += textwrap.indent(self._comment, "! ", lambda line: True)
        comment += "\n\n"

        # prepare body
        formatted_records = []
        with self._dev_set_current_model_file_path(model_file_path):
            for table_ref, table in self._tables.items():  # self._tables is already sorted
                formatted_records.extend([r.to_idf(external_files_mode=external_files_mode) for r in sorted(table)])
        body = "\n\n".join(formatted_records)

        # return
        content = comment + body
        return multi_mode_write(
            lambda f: f.write(content),
            lambda: content,
            buffer_or_path
        )
