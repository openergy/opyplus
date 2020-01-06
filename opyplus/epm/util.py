"""Util functions for opyplus epm package."""
import json

from ..util import multi_mode_write


def json_data_to_json(json_data, buffer_or_path=None, indent=2):
    """
    Write a json-serializable dict to a string or file.

    Parameters
    ----------
    json_data: dict
    buffer_or_path: typing.StringIO or str or None
        buffer or file path to write the json to, if None (default) the function returns a json string
    indent: int or None
        indent parameter passed to json.dump

    Returns
    -------
    str or None
        str if buffer_or_path is None else None
    """
    return multi_mode_write(
        lambda buffer: json.dump(json_data, buffer, indent=indent),
        lambda: json.dumps(json_data, indent=indent),
        buffer_or_path=buffer_or_path
    )
