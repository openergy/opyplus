"""Useful functions for idd manipulation."""
from ..epm.external_file import ExternalFile


def isinstance_str(value):
    """
    Check if value is a string.

    Parameters
    ----------
    value

    Returns
    -------
    bool
    """
    return isinstance(value, (str, ExternalFile))


def table_name_to_ref(name):
    """
    Convert table name to ref.

    Parameters
    ----------
    name: str

    Returns
    -------
    str
    """
    return name.replace(":", "_")
