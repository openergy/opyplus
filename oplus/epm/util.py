import json


def table_name_to_ref(name):
    return name.replace(":", "_")


def json_data_to_json(json_data, buffer_or_path=None, indent=2):
    is_path = False
    if isinstance(buffer_or_path, str):
        is_path = True
        buffer_or_path = open(buffer_or_path, "w")

    try:
        if buffer_or_path is None:
            return json.dumps(json_data, indent=indent)
        return json.dump(json_data, buffer_or_path, indent=indent)
    finally:
        if is_path:
            buffer_or_path.close()

