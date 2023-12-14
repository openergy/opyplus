from ..epm.parse_idf import parse_idf
from ..epm.table import Table
from ..epm.epm import Epm
import collections
from ..epm.relations_manager import RelationsManager
from .. import CONF
import logging

logger = logging.getLogger(__name__)

DDY_TABLE_DESCRIPTORS_REF = ["sizingperiod_designday",
                             "site_location",
                             "runperiodcontrol_daylightsavingtime"]


class Ddy(Epm):
    """
    Ddy model.

    Ddy is an EnergyPlus DesignDay model
    It can come from a .ddy file, available on https://energyplus.net/weather

    Ddy files follow same santard as Idf but only contains design conditions EnergyPlus objects
    A Ddy contains:
        SiteLocation
        SizingPeriod_DesignDay: list of design days
        RunPeriodControl_DaylightSavingTime

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
    Ddy files are not versioned, and by default will use latest IDD version for model conversion from .ddy
    """

    def __init__(self, json_data=None, check_required=True, check_length=True, idd_or_version=None):
        # call super
        super().__init__(
            json_data=json_data,
            check_required=check_required,
            check_length=check_length,
            idd_or_version=idd_or_version
        )
        # !! relations manager must be defined before table creation because table creation will trigger
        # hook registering
        self._dev_relations_manager = RelationsManager(self)

        self._tables = collections.OrderedDict(sorted([  # {lower_ref: table, ...}
            (table_descriptor.table_ref.lower(), Table(table_descriptor, self))
            for table_descriptor in self._dev_idd.table_descriptors.values()
            if table_descriptor.table_ref.lower() in DDY_TABLE_DESCRIPTORS_REF
        ]))

        # load json_data if relevant
        if json_data is not None:
            self._dev_populate_from_json_data(json_data)

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
        Load Ddy from a .ddy file.

        Returns
        -------
        Ddy
        """
        return cls._create_from_buffer_or_path(
            parse_idf,
            buffer_or_path,
            idd_or_version=CONF.default_idd_version  # .ddy are not version: latest idd is used
        )

    def get_design_day_dict(self, ref):
        """
        Dump the Epm to a json-serializable dict.

        Returns
        -------
        dict
            A dictionary of serialized data.
        """
        # create data
        design_day = self.sizingperiod_designday.one(lambda x: ref in x.name)
        design_day_dict = {design_day.get_field_descriptor(field).ref: design_day[field] for field in
                           range(len(design_day))}

        return design_day_dict

    def copy_to_epm(self, epm, ref=None):
        """
        Dump the Epm to a json-serializable dict.

        Returns
        -------
        dict
            A dictionary of serialized data.
        """
        # create data
        design_day_dict = self.get_design_day_dict()

        epm.sizingperiod_designday.add(
            design_day_dict
        )
