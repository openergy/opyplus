import os

IDD_DIR_PATH = os.path.realpath(os.path.dirname(__file__))


def get_latest_idd_version():
    last_file_name = sorted(os.listdir(IDD_DIR_PATH))[-1]
    major, minor, patch, _ = last_file_name[1:].split("-")
    return int(major), int(minor), 0


def get_idd_path(version):
    major, minor, patch = version
    path = os.path.join(IDD_DIR_PATH, f"V{major}-{minor}-0-Energy+.idd")
    # check exists
    if not os.path.isfile(path):
        raise ValueError(f"No idd was found for version {version}.")
    return path
