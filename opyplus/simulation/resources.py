import os
import logging

from opyplus import CONF

logger = logging.getLogger(__name__)

INFO_FILE_NAME = "#opyplus.info"


class ResourcesRefs:
    # eplus
    idf = "idf"
    epw = "epw"
    eio = "eio"
    eso = "eso"
    mtr = "mtr"
    mtd = "mtd"
    mdd = "mdd"
    err = "err"
    summary_table = "summary_table"

    # opyplus
    info = "info"

    @classmethod
    def values(cls):
        return [k for k, v in cls.__dict__.items() if isinstance(v, str) and k[0] != "_"]


def get_resource_ref(file_name):
    base_name, ext = os.path.splitext(file_name)
    ref = ext[1:]

    # by extension
    if ref in (
        ResourcesRefs.idf,
        ResourcesRefs.epw,
        ResourcesRefs.eio,
        ResourcesRefs.eso,
        ResourcesRefs.mtr,
        ResourcesRefs.mtd,
        ResourcesRefs.mdd

    ):
        return ref

    # err
    if ref == ResourcesRefs.err and base_name != "sqlite":
        return ref

    # summary table
    if file_name[-9:] == "Table.csv":
        return ResourcesRefs.summary_table
    if file_name == "eplustbl.csv":
        return ResourcesRefs.summary_table

    # info
    if file_name == INFO_FILE_NAME:
        return ResourcesRefs.info

    # not a known resource
    return None


def create_resources_map(dir_path):
    # check dir exists
    if not os.path.isdir(dir_path):
        raise NotADirectoryError(f"directory not found: {dir_path}")

    # prepare empty resources map
    resources = {k: None for k in ResourcesRefs.values()}  # {ref: rel_path, ...

    # explore possible paths
    for sub_dir in (None, "Output"):
        scan_path = dir_path if sub_dir is None else os.path.join(dir_path, sub_dir)
        if not os.path.isdir(scan_path):
            continue
        for file_name in os.listdir(scan_path):
            # find ref
            ref = get_resource_ref(file_name)

            # skip if not ref
            if ref is None:
                continue

            # create file path
            file_rel_path = file_name if sub_dir is None else os.path.join(sub_dir, file_name)

            # check not already registered
            if resources[ref] is not None:
                logger.warning(
                    f"'{ref}' file found was detected more than once, skiping.\n"
                    f" - used file: {resources[ref]}\n"
                    f" - skipped file: {file_rel_path}\n"
                )
                continue

            # register
            resources[ref] = file_rel_path

    return resources


def get_opyplus_path(simulation_path, ref):
    if ref == ResourcesRefs.info:
        return os.path.join(simulation_path, INFO_FILE_NAME)
    if ref in (ResourcesRefs.idf, ResourcesRefs.epw):
        return os.path.join(simulation_path, f"{CONF.default_model_name}.{ref}")
    raise ValueError(f"non relevant ref for called function: '{ref}'")
