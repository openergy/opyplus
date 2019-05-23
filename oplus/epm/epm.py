"""
create/update/delete framework methods (see methods documentation):
 - epm._dev_populate_from_json_data
 - table.batch_add
 - record.update
 - queryset.delete
 - record.delete
"""

import os
import collections
import textwrap
import json

from .. import CONF
from ..util import get_multi_line_copyright_message, to_buffer
from .idd import Idd
from .table import Table
from .record import Record
from .relations_manager import RelationsManager
from .external_files_manager import ExternalFilesManager
from .external_file import get_external_files_dir_name
from .parse_idf import parse_idf
from .util import json_data_to_json, multi_mode_write, table_name_to_ref


def default_external_files_dir_name(model_name):
    """
    Parameters
    ----------
    model_name: with or without extension
    """
    name, ext = os.path.splitext(model_name)
    return name + CONF.external_files_suffix


class Epm:
    """
    Energyplus model
    """
    _dev_record_cls = Record  # for subclassing
    _dev_table_cls = Table  # for subclassing
    _dev_idd_cls = Idd  # for subclassing

    def __init__(self, check_required=True, check_length=True, idd_or_buffer_or_path=None):
        """
        An Epm is an Energy Plus Model.
        It can come from and idf, a epjson (not coded yet), or a json.
        It can be transformed in an idf, an epjson (not coded yet) or a json.

        Parameters
        ----------
        idd_or_buffer_or_path: (expert) if you wan't to use a specific idd.
        check_length: boolean, default True
            If True, will raise an exception if a field has a bigger length than authorized. If False, will not check.
        check_required: boolean, default True
            If True, will raise an exception if a required field is missing. If False, not not perform any checks.
        """
        self._dev_idd = (
            idd_or_buffer_or_path if isinstance(idd_or_buffer_or_path, Idd) else
            self._dev_idd_cls(idd_or_buffer_or_path)
        )
        # !! relations manager must be defined before table creation because table creation will trigger
        # hook registering
        self._dev_relations_manager = RelationsManager(self)

        # external files manager
        self._dev_external_files_manager = ExternalFilesManager(self)

        self._tables = collections.OrderedDict(sorted([  # {lower_ref: table, ...}
            (table_descriptor.table_ref.lower(), Table(table_descriptor, self))
            for table_descriptor in self._dev_idd.table_descriptors.values()
        ]))

        self._dev_check_required = check_required
        self._dev_check_length = check_length
        self._comment = ""

    # ------------------------------------------ private ---------------------------------------------------------------
    @classmethod
    def _create_from_buffer_or_path(
            cls,
            parse_fct,
            buffer_or_path,
            idd_or_buffer_or_path=None,
            check_required=True,
            check_length=True,
            load_only=None
    ):
        # prepare buffer
        _source_file_path, buffer = to_buffer(buffer_or_path)

        # create json data
        with buffer as f:
            json_data = parse_fct(f)

        # create and return epm
        return cls.from_json_data(
            json_data,
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required,
            check_length=check_length,
            load_only=load_only
        )

    # ------------------------------------------ dev api ---------------------------------------------------------------
    def _dev_populate_from_json_data(self, json_data):
        """
        !! Must only be called once, when empty !!
        """

        # workflow
        # --------
        # (methods belonging to create/update/delete framework:
        #     epm._dev_populate_from_json_data, table.batch_add, record.update, queryset.delete, record.delete)
        # 1. add inert
        #     * data is checked
        #     * old links are unregistered
        #     * record is stored in table (=> pk uniqueness is checked)
        # 2. activate: hooks, links, external files

        # manage comment if any
        comment = json_data.pop("_comment", None)
        if comment is not None:
            self._comment = comment

        # populate external files
        external_files_data = json_data.pop("_external_files", dict())
        self._dev_external_files_manager.populate_from_json_data(external_files_data)

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

        # activate links and external files
        for r in added_records:
            r._dev_activate_links()
            r._dev_activate_external_files()

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
        """
        An external file manages file paths.
        """
        external_files = []
        for table in self._tables.values():
            for r in table:
                external_files.extend([ef for ef in r.get_external_files()])
        return external_files

    # construct
    def set_comment(self, comment):
        self._comment = str(comment)

    def set_defaults(self):
        """
        All fields of Epm with a default value and that are null will be set to their default value.
        """
        for table in self._tables.values():
            for r in table:
                r.set_defaults()

    def dump_external_files(self, target_dir_path=None):
        """
        Parameters
        ----------
        target_dir_path
        """
        self._dev_external_files_manager.dump_external_files(target_dir_path=target_dir_path)

    # ------------------------------------------- load -----------------------------------------------------------------
    @classmethod
    def from_json_data(cls,
                       json_data,
                       check_required=True,
                       check_length=True,
                       idd_or_buffer_or_path=None,
                       load_only=None):
        """
        Parameters
        ----------
        json_data: dict
            Dictionary of serialized data (text, floats, ints, ...). For more information on data structure, create an
            Epm and use to_json_data or to_json.
        check_required: boolean, default True
            If True, will raise an exception if a required field is missing. If False, not not perform any checks.
        check_length: boolean, default True
            If True, will raise an exception if a field has a bigger length than authorized. If False, will not check.
        idd_or_buffer_or_path: (expert) to load using a custom idd
        load_only: iterable, default None
            iterable of table names or refs which you want to load. All other tables will be skipped.

        Returns
        -------
        An Epm instance.
        """
        # remove skipped tables if relevant
        if load_only is not None:
            load_only = set(table_name_to_ref(t) for t in load_only)
            json_data = {k: v for (k, v) in json_data.items() if (k in load_only or k[0] == "_")}

        epm = cls(
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required,
            check_length=check_length
        )

        epm._dev_populate_from_json_data(json_data)
        return epm

    @classmethod
    def from_idf(cls,
                 buffer_or_path,
                 check_required=True,
                 check_length=True,
                 idd_or_buffer_or_path=None,
                 load_only=None):
        """
        Parameters
        ----------
        buffer_or_path: idf buffer or path
        check_required: boolean, default True
            If True, will raise an exception if a required field is missing. If False, not not perform any checks.
        check_length: boolean, default True
            If True, will raise an exception if a field has a bigger length than authorized. If False, will not check.
        idd_or_buffer_or_path: (expert) to load using a custom idd
        load_only: iterable, default None
            iterable of table names or refs which you want to load. All other tables will be skipped.

        Returns
        -------
        An Epm instance.
        """
        # fixme: [load-geometry-only] add geometry only (or equivalent)
        return cls._create_from_buffer_or_path(
            parse_idf,
            buffer_or_path,
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required,
            check_length=check_length,
            load_only=load_only
        )

    @classmethod
    def from_json(cls,
                  buffer_or_path,
                  check_required=True,
                  check_length=True,
                  idd_or_buffer_or_path=None,
                  load_only=None):
        """
        Parameters
        ----------
        buffer_or_path: json buffer or path
        check_required: boolean, default True
            If True, will raise an exception if a required field is missing. If False, not not perform any checks.
        check_length: boolean, default True
            If True, will raise an exception if a field has a bigger length than authorized. If False, will not check.
        idd_or_buffer_or_path: (expert) to load using a custom idd
        load_only: iterable, default None
            iterable of table names or refs which you want to load. All other tables will be skipped.

        Returns
        -------
        An Epm instance.
        """
        return cls._create_from_buffer_or_path(
            json.load,
            buffer_or_path,
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required,
            check_length=check_length,
            load_only=load_only
        )

    # ----------------------------------------- export -----------------------------------------------------------------
    def to_json_data(self):
        """
        Returns
        -------
        A dictionary of serialized data.
        """
        # create data
        d = collections.OrderedDict((t.get_ref(), t.to_json_data()) for t in self._tables.values())
        d["_comment"] = self._comment
        d.move_to_end("_comment", last=False)
        d["_external_files"] = self._dev_external_files_manager
        return d

    def to_json(self, buffer_or_path=None, indent=2):
        """
        Parameters
        ----------
        buffer_or_path: buffer or path, default None
            output to write into. If None, will return a json string.
        indent: int, default 2
            Defines the indentation of the json

        Returns
        -------
        None, or a json string (if buffer_or_path is None).
        """
        # return json
        return json_data_to_json(
            self.to_json_data(),
            buffer_or_path=buffer_or_path,
            indent=indent
        )
        
    def to_idf(self, buffer_or_path=None, dump_external_files=True):
        """
        Parameters
        ----------
        buffer_or_path: buffer or path, default None
            output to write into. If None, will return a json string.
        dump_external_files: boolean, default True
            if True, external files will be dumped in external files directory

        Returns
        -------
        None, or an idf string (if buffer_or_path is None).
        """
        # prepare comment
        comment = get_multi_line_copyright_message()
        if self._comment != "":
            comment += textwrap.indent(self._comment, "! ", lambda line: True)
        comment += "\n\n"

        # prepare external files dir path if file path
        if isinstance(buffer_or_path, str):
            dir_path, file_name = os.path.split(buffer_or_path)
            model_name, _ = os.path.splitext(file_name)
        else:
            model_name, dir_path = None, os.path.curdir

        # dump files if asked
        if dump_external_files:
            self.dump_external_files(
                target_dir_path=os.path.join(dir_path, get_external_files_dir_name(model_name=model_name))
            )

        # prepare body
        formatted_records = []
        for table_ref, table in self._tables.items():  # self._tables is already sorted
            formatted_records.extend([r.to_idf(model_name=model_name) for r in sorted(table)])
        body = "\n\n".join(formatted_records)

        # return
        content = comment + body
        return multi_mode_write(
            lambda f: f.write(content),
            lambda: content,
            buffer_or_path
        )
