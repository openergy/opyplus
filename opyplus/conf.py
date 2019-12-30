"""Opyplus configuration."""

from .idd.resources import get_latest_idd_version


class CONF:
    """
    Opyplus configuration class.

    Attributes
    ----------
    encoding: str
        default encoding used to parse files
    default_model_name: str
    external_files_suffix: str
    default_idd_version: int, int, int
    """

    encoding = "latin-1"  # even needed for example files...
    default_model_name = "opyplus"
    external_files_suffix = "-external"
    default_idd_version = get_latest_idd_version()  # use if we create an empty epm without specifying version
