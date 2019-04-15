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
from .parse_idf import parse_idf
from .util import json_data_to_json, multi_mode_write


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

    def __init__(self, check_required=True, idd_or_buffer_or_path=None):
        """
        An Epm is an Energy Plus Model.
        It can come from and idf, a epjson (not coded yet), or a json.
        It can be transformed in an idf, an epjson (not coded yet) or a json.

        Parameters
        ----------
        idd_or_buffer_or_path: (expert) if you wan't to use a specific idd.
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

        self._tables = collections.OrderedDict(sorted([  # {lower_ref: table, ...}
            (table_descriptor.table_ref.lower(), Table(table_descriptor, self))
            for table_descriptor in self._dev_idd.table_descriptors.values()
        ]))

        self._dev_check_required = check_required
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
    def _dev_populate_from_json_data(self, json_data, model_file_path=None):
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
            records = table._dev_add_inert(json_data_records, model_file_path=model_file_path)

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

    def gather_external_files(self, target_dir_path, mode="copy", check_files_exist=True):
        """
        Parameters
        ----------
        target_dir_path
        mode: str, default 'copy'
            'copy', 'move', 'set_back'
        check_files_exist: boolean, default True

        This will move all of the external files towards a given directory (target_dir_path).

        Three different modes exist:
          - 'copy': files will be copied
          - 'move': files will be cut/pasted
          - 'set_back': files will not be impacted, but ExternalFiles path will be changed to new target path

        If 'copy' or 'move':
         - files of the os will be impacted
         - they therefore must exist (even if check_files_exist if False)
         - ExternalFiles path will be changed to new target path

        If 'set_back':
         - files of the os will not be impacted
         - they therefore don't have to exist (except if check_files_exist is True)
         - ExternalFiles path will be changed to new target path
        """
        # collect external files
        external_files = self.get_external_files()

        # leave if no external files
        if len(external_files) == 0:
            return

        # check that all external files exists
        if check_files_exist or mode in ("copy", "move"):
            for ef in external_files:
                ef.check_file_exists()

        # prepare directory (or check existing) if copy or move
        if mode != "set_back":
            if not os.path.exists(target_dir_path):
                os.mkdir(target_dir_path)
            elif not os.path.isdir(target_dir_path):
                raise NotADirectoryError(f"given dir_path is not a directory: {target_dir_path}")

        # copy or move files
        raise_if_not_found = True if mode == "copy" else False
        # since file may already have been moved, and since we checked that all files existed, we don't raise
        # if file is not found
        for ef in external_files:
            ef.transfer(target_dir_path, mode=mode, raise_if_not_found=raise_if_not_found)

    # ------------------------------------------- load -----------------------------------------------------------------
    @classmethod
    def from_json_data(cls, json_data, check_required=True, model_file_path=None, idd_or_buffer_or_path=None):
        """
        Parameters
        ----------
        json_data: dict
            Dictionary of serialized data (text, floats, ints, ...). For more information on data structure, create an
            Epm and use to_json_data or to_json.
        check_required: boolean, default True
            If True, will raise an exception if a required field is missing. If False, not not perform any checks.
        model_file_path: str, default current directory
            If json data contains external files, which are defined by a relative path (and not absolute), oplus needs
            to convert them to an absolute path. model_file_path defines the reference used for this conversion.
        idd_or_buffer_or_path: (expert) to load using a custom idd

        Returns
        -------
        An Epm instance.
        """
        epm = cls(
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required
        )

        epm._dev_populate_from_json_data(json_data, model_file_path=model_file_path)
        return epm

    @classmethod
    def from_idf(cls, buffer_or_path, check_required=True, model_file_path=None, idd_or_buffer_or_path=None):
        """
        Parameters
        ----------
        buffer_or_path: idf buffer or path
        check_required: boolean, default True
            If True, will raise an exception if a required field is missing. If False, not not perform any checks.
        model_file_path: str, default idf path or current directory
            If json data contains external files, which are defined by a relative path (and not absolute), oplus needs
            to convert them to an absolute path. model_file_path defines the reference used for this conversion.
            If model_file_path is not given:
                - if idf is given through a path (not a buffer): the idf path will be used
                - else: the current directory will be used
        idd_or_buffer_or_path: (expert) to load using a custom idd

        Returns
        -------
        An Epm instance.
        """
        return cls._create_from_buffer_or_path(
            parse_idf,
            buffer_or_path,
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required,
            model_file_path=model_file_path
        )

    @classmethod
    def from_json(cls, buffer_or_path, check_required=True, model_file_path=None, idd_or_buffer_or_path=None):
        """
        Parameters
        ----------
        buffer_or_path: json buffer or path
        check_required: boolean, default True
            If True, will raise an exception if a required field is missing. If False, not not perform any checks.
        model_file_path: str, default json path or current directory
            If json data contains external files, which are defined by a relative path (and not absolute), oplus needs
            to convert them to an absolute path. model_file_path defines the reference used for this conversion.
            If model_file_path is not given:
                - if json is given through a path (not a buffer): the json path will be used
                - else: the current directory will be used
        idd_or_buffer_or_path: (expert) to load using a custom idd

        Returns
        -------
        An Epm instance.
        """
        return cls._create_from_buffer_or_path(
            json.load,
            buffer_or_path,
            idd_or_buffer_or_path=idd_or_buffer_or_path,
            check_required=check_required,
            model_file_path=model_file_path
        )

    # ----------------------------------------- export -----------------------------------------------------------------
    def to_json_data(self, external_files_mode=None, model_file_path=None):
        """
        Parameters
        ----------
        external_files_mode: str, default 'relative'
            'relative', 'absolute'
            The external files paths will be written in an absolute or a relative fashion.
        model_file_path: str, default current directory
            If 'relative' file paths, oplus needs to convert absolute paths to relative paths. model_file_path defines
            the reference used for this conversion. If not given, current directory will be used.

        Returns
        -------
        A dictionary of serialized data.
        """
        # create data
        d = collections.OrderedDict(
            (t.get_ref(), t.to_json_data(
                external_files_mode=external_files_mode,
                model_file_path=model_file_path)
             ) for t in self._tables.values()
        )
        d["_comment"] = self._comment
        d.move_to_end("_comment", last=False)
        return d

    def to_json(self, buffer_or_path=None, indent=2, external_files_mode=None, model_file_path=None):
        """
        Parameters
        ----------
        buffer_or_path: buffer or path, default None
            output to write into. If None, will return a json string.
        indent: int, default 2
            Defines the indentation of the json
        external_files_mode: str, default 'relative'
            'relative', 'absolute'
            The external files paths will be written in an absolute or a relative fashion.
        model_file_path: str, default current directory
            If 'relative' file paths, oplus needs to convert absolute paths to relative paths. model_file_path defines
            the reference used for this conversion. If not given, current directory will be used.

        Returns
        -------
        None, or a json string (if buffer_or_path is None).
        """
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
        """
        Parameters
        ----------
        buffer_or_path: buffer or path, default None
            output to write into. If None, will return a json string.
        external_files_mode: str, default 'relative'
            'relative', 'absolute'
            The external files paths will be written in an absolute or a relative fashion.
        model_file_path: str, default current directory
            If 'relative' file paths, oplus needs to convert absolute paths to relative paths. model_file_path defines
            the reference used for this conversion. If not given, current directory will be used.

        Returns
        -------
        None, or an idf string (if buffer_or_path is None).
        """
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
        for table_ref, table in self._tables.items():  # self._tables is already sorted
            formatted_records.extend([r.to_idf(
                external_files_mode=external_files_mode,
                model_file_path=model_file_path) for r in sorted(table)])
        body = "\n\n".join(formatted_records)

        # return
        content = comment + body
        return multi_mode_write(
            lambda f: f.write(content),
            lambda: content,
            buffer_or_path
        )
