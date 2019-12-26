from ..epm.external_file import ExternalFile


def isinstance_str(value):
    return isinstance(value, (str, ExternalFile))


def table_name_to_ref(name):
    return name.replace(":", "_")
