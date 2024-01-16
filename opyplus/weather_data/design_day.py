"""Ddy design day module."""

from ..epgm.parse_idf import parse_idf
from ..epgm.epgm import Epgm
from .. import CONF
import logging

logger = logging.getLogger(__name__)

DDY_TABLE_DESCRIPTORS_REF = (
    "sizingperiod_designday",
    "site_location",
    "runperiodcontrol_daylightsavingtime",
)


class Ddy(Epgm):
    """
    Ddy model.

    Ddy is an EnergyPlus DesignDay model
    It can come from a .ddy file, available on https://energyplus.net/weather

    Ddy files follow same standard as Idf but only contains design conditions EnergyPlus objects
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
    Ddy version behaviour
        Ddy files are not versioned, and by default will use latest IDD version for model conversion from .ddy
    """

    _dev_restrict_table_refs = DDY_TABLE_DESCRIPTORS_REF

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
        {'<Ddy>'}
        """
        return "<Ddy>"

    def __str__(self):
        """
        Str representation of Ddy, with the number of records per tables.

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

    # def get_design_day_dict(self, design_day_ref):
    #     """
    #     Get design day from ref as dict.
    #
    #     Parameters
    #     ----------
    #     design_day_ref
    #
    #     Returns
    #     -------
    #     design_day_dict
    #     """
    #     design_day_select = self.sizingperiod_designday.select(lambda x: design_day_ref in x.name)
    #     if len(design_day_select) == 0:
    #         raise ValueError(f"Design day with name '{design_day_ref}' not found.")
    #     if len(design_day_select) > 1:
    #         raise ValueError(
    #             f"Ambiguous design day selection, "
    #             f"{len(design_day_select)} design days containing ref '{design_day_ref}' were found, be more concise.")
    #
    #     design_day_data = self.sizingperiod_designday.one(lambda x: design_day_ref in x.name).to
    #     # design_day_data = {design_day.get_field_descriptor(field).ref: design_day[field] for field in
    #     #                    range(len(design_day))}
    #     return design_day_data

    def add_design_day_to_epm(self, epm, design_day_ref):
        """
        Add design day to Epm.

        Parameters
        ----------
        epm
        design_day_ref
        """
        # get design day as dict
        design_day_dict = self.get_design_day_dict(design_day_ref)

        epm.sizingperiod_designday.add(
            design_day_dict
        )

    # ------------------------------------------- save/load ------------------------------------------------------------
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
            idd_or_version=CONF.default_idd_version
        )
