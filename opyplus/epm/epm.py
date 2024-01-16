"""
Module to handle idf files as python objects (EnergyPlus Model).

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
import logging

from .. import CONF
from ..util import get_multi_line_copyright_message, to_buffer, version_str_to_version
from ..idd.idd import Idd
from .table import Table
from .record import Record
from .relations_manager import RelationsManager
from .external_files_manager import ExternalFilesManager
from .external_file import get_external_files_dir_name
from .parse_idf import parse_idf
from .util import json_data_to_json, multi_mode_write
from .epsf import Epsf

def default_external_files_dir_name(model_name):
    """
    Get default dir name for external files.

    Parameters
    ----------
    model_name: with or without extension

    Returns
    -------
    str
    """
    name, ext = os.path.splitext(model_name)
    return name + CONF.external_files_suffix


logger = logging.getLogger(__name__)

# the order of the records of these tables matter
NON_SORTABLE_TABLE_REFS = ("energymanagementsystem_programcallingmanager",)


class Epm(Epsf):
    """
    Energyplus model.

    An Epm is an Energy Plus Model.
    It can come from and idf, a epjson (not coded yet), or a json.
    It can be transformed in an idf, an epjson (not coded yet) or a json.

    Parameters
    ----------
    json_data: json serializable object, default None
        if provided, Epm will be filled with given objects
    check_length: boolean, default True
        If True, will raise an exception if a field has a bigger length than authorized. If False, will not check.
    check_required: boolean, default True
        If True, will raise an exception if a required field is missing. If False, not not perform any checks.
    idd_or_version: (expert) if you want to use a specific idd, you can require a specific version (x.x.x), or
        directly provide an IDD object.

    Notes
    -----
    Eplus version behaviour:

        - if idd_or_version is provided, required idd will be used (may trigger a warning if it is not coherent with
          json_data version, if any)

        - else if json_data is provided: will use proper idd (according to version field) or trigger a warning if idd is
          not available and will choose the closest

        - else will use default eplus version used in conf, which is initially set to latest available idd version
    """

    def __init__(self, json_data=None, check_required=True, check_length=True, idd_or_version=None):
        # call super
        super().__init__(
            json_data=json_data,
            check_required=check_required,
            check_length=check_length,
            idd_or_version=idd_or_version
        )



    # --------------------------------------------- public api ---------------------------------------------------------
    # python magic
    def __repr__(self):
        """
        Repr.

        Returns
        -------
        {'<Epm>'}
        """
        return "<Epm>"

    def __str__(self):
        """
        Str representation of Epm, with the number of records per tables.

        Returns
        -------
        str
        """
        s = "Epm\n"

        for table in self._tables.values():
            records_nb = len(table)
            if records_nb == 0:
                continue
            plural = "" if records_nb == 1 else "s"
            s += f"  {table.get_name()}: {records_nb} record{plural}\n"

        return s.strip()



    # ------------------------------------------- save/load ------------------------------------------------------------
    @classmethod
    def load(
            cls,
            buffer_or_path,
            check_required=True,
            check_length=True,
            idd_or_version=None
    ):
        """
        Load Epm from a file.

        Parameters
        ----------
        buffer_or_path: str or typing.StringIO
            idf buffer or path
        check_required: bool
            If True (default), will raise an exception if a required field is missing.
            If False, do not perform any checks.
        check_length: bool
            If True (default), will raise an exception if a field has a bigger length than authorized.
            If False, will not check.

        Other Parameters
        ----------------
        idd_or_version: tuple or Idd
            If you want to use a specific idd, you can require a specific version (x.x.x),
            or directly provide an IDD object.

        Returns
        -------
        Epm
        """
        return cls().from_idf(
            buffer_or_path,
            check_required=check_required,
            check_length=check_length,
            idd_or_version=idd_or_version
        )

    def save(self, buffer_or_path=None, dump_external_files=True):
        """
        Save Epm to a file.

        Parameters
        ----------
        buffer_or_path: typing.StringIO or str or None
            output to write into. If None, will return a json string.
        dump_external_files: boolean, default True
            if True, external files will be dumped in external files directory

        Returns
        -------
        str or None
            None, or an idf string (if buffer_or_path is None).
        """
        return self.to_idf(buffer_or_path=buffer_or_path, dump_external_files=dump_external_files)

    # --------------------------------------- import/export ------------------------------------------------------------
    # ----------- idf
    @classmethod
    def from_idf(
            cls,
            buffer_or_path,
            check_required=True,
            check_length=True,
            idd_or_version=None
    ):
        """See load."""
        cls.from_epsf(
            buffer_or_path,
            check_required,
            check_length,
            idd_or_version
            )


    def to_idf(self, buffer_or_path=None, dump_external_files=True):
        """See save."""
        self.to_epsf(buffer_or_path,dump_external_files)
