"""Useful functions for idd manipulation."""
from ..epgm.external_file import ExternalFile


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


def get_field_attribute_extended_value(field_attribute, index, extensible_info):
    cycle_start, cycle_len, _ = extensible_info
    cycle_num = (index - cycle_start) // cycle_len
    return None if field_attribute is None else field_attribute.replace("1", str(cycle_num + 1))
