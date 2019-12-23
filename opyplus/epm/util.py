import json

from ..util import multi_mode_write


def json_data_to_json(json_data, buffer_or_path=None, indent=2):
    return multi_mode_write(
        lambda buffer: json.dump(json_data, buffer, indent=indent),
        lambda: json.dumps(json_data, indent=indent),
        buffer_or_path=buffer_or_path
    )
