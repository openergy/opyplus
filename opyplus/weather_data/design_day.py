"""Weather data design condition module."""
from ..util import get_multi_line_copyright_message, to_buffer, version_str_to_version
from ..epm.parse_idf import parse_idf
from ..epm.table import Table
from ..epm.record import Record
from ..epm.epm import Epm
import collections


class Ddy(Epm):
    """
    Class describing E+ weather data design condition.

    Parameters
    ----------
    name: str
    values: list

    Attributes
    ----------
    name: str
    values: list
    """

    def __init__(self, json_data=None, check_required=True, check_length=True, idd_or_version=None):
        # call super
        super().__init__(
            json_data=json_data,
            check_required=check_required,
            check_length=check_length,
            idd_or_version=idd_or_version
        )
        # create empty general permanent record if no json_data
        self._tables = collections.OrderedDict(sorted([  # {lower_ref: table, ...}
            (table_descriptor.table_ref.lower(), Table(table_descriptor, self))
            for table_descriptor in self._dev_idd.table_descriptors.values() if
            "sizingperiod_designday" in table_descriptor.table_ref.lower()
        ]))

    # --------------------------------------------- public api ---------------------------------------------------------
    # python magic
    def __repr__(self):
        """
        Repr.

        Returns
        -------
        {'<Epm>'}
        """
        return "<Ddy>"

    def __str__(self):
        """
        Str representation of Epm, with the number of records per tables.

        Returns
        -------
        str
        """
        s = "Ddy\n"

        for table in self._tables.values():
            records_nb = len(table)
            if records_nb == 0:
                continue
            plural = "" if records_nb == 1 else "s"
            s += f"  {table.get_name()}: {records_nb} record{plural}\n"

        return s.strip()

    @classmethod
    def from_ddy(
            cls,
            buffer_or_path
    ):
        """
        Load Ddy from a file.

        Returns
        -------
        Ddy
        """
        return cls().from_idf(
            buffer_or_path=buffer_or_path

        )
