import platform
import re
import os
import collections


# ------------------------------------------ private -------------------------------------------------------------------
def _get_value_by_version(d):
    """
    Finds the value depending in current eplus version.


    Parameters
    ----------
    d: dict
        {(0, 0): value, (x, x): value, ...}
        for current version (cv), current value is the value of version v such as v <= cv < v+1
    """
    from oplus import CONF  # touchy import

    cv = CONF.eplus_version[:2]
    for v, value in sorted(d.items(), reverse=True):
        if cv >= v:
            return value


def _make_enum(*keys):
    Enum = collections.namedtuple("Enum", keys)
    return Enum(**dict([(k, k) for k in keys]))

# -------------------------------------- operating system --------------------------------------------------------------
SYS_NAME = platform.system()
if SYS_NAME in ("Windows",):  # windows
    OS_NAME = "windows"
elif SYS_NAME in ("Darwin",):  # mac osx
    OS_NAME = "osx"
elif SYS_NAME in ("Linux",):  # linux
    OS_NAME = "linux"
else:
    raise RuntimeError("Unknown platform.system(): '%s'." % SYS_NAME)


# ---------------------------------------- app dir path ----------------------------------------------------------------
if OS_NAME == "windows":
    APPS_DIR_PATH, EPLUS_DIR_PATTERN = r"C:\\", re.compile("EnergyPlusV(\d*)-(\d*)-(\d*)")
elif OS_NAME == "osx":  # mac osx
    APPS_DIR_PATH, EPLUS_DIR_PATTERN = "/Applications", re.compile("EnergyPlus-(\d*)-(\d*)-(\d*)")
elif OS_NAME == "linux":  # linux
    APPS_DIR_PATH, EPLUS_DIR_PATTERN = "/usr/local", re.compile("EnergyPlus-(\d*)-(\d*)-(\d*)")
else:
    raise RuntimeError("Unknown os_name: '%s'" % OS_NAME)


# --------------------------------------------- outputs ----------------------------------------------------------------
OUTPUT_FILES_LAYOUTS = _make_enum(
    "eplusout",  # {simulation_dir_path}/eplusout.{extension}
    "simu",  # {simulation_dir_path}/{simulation_base_name}.{extension}
    "output_simu",  # {simulation_dir_path}/Output/{simulation_base_name}.{extension}
    "simu_table",  # {simulation_dir_path}/{simulation_base_name}Table.csv
    "output_simu_table",  # {simulation_dir_path}/Output/{simulation_base_name}Table.csv
    "eplustbl",  # {simulation_dir_path}/eplusout.csv
)

_layouts_matrix = {
    "windows": {
        "inputs": {
            (0, 0):  "simu",
            (8, 2): "eplusout"
        },
        "table": {
            (0, 0): "simu_table",
            (8, 2): "eplustbl",
        },
        "other": {
            (0, 0): "simu",
            (8, 2): "eplusout"
        }
    },
    "osx": {
        "inputs": {
            (0, 0): "output_simu",
            (8, 2): "simu"

        },
        "table": {
            (0, 0): "output_simu_table",
            (8, 2): "eplustbl",
        },
        "other": {
            (0, 0): "output_simu",
            (8, 2): "eplusout"
        }
    },
    "linux": {
        "inputs": {
            (0, 0): "output_simu",
            (8, 5): "eplusout"

        },
        "table": {
            (0, 0): "output_simu_table",
            (8, 5): "eplustbl",
        },
        "other": {
            (0, 0): "output_simu",
            (8, 5): "eplusout"
        }
    }
}


def get_output_files_layout(output_category):
    """
    Parameters
    ----------
    output_category: str
        inputs: epw, idf
        table: summary table
        other: other
    """
    # check  category
    assert output_category in ("inputs", "table", "other")

    # get version dict
    layouts = _layouts_matrix[OS_NAME][output_category]

    # get version
    return _get_value_by_version(layouts)


# --------------------------------------------- epw path ---------------------------------------------------------------
def get_simulated_epw_path():
    """
    Returns
    -------
    None if epw can be anywhere
    """
    from oplus import CONF  # touchy imports

    if OS_NAME == "windows":
        return os.path.join(CONF.eplus_base_dir_path, "WeatherData", "%s.epw" % CONF.simulation_base_name)

    #  on linux or osx, epw may remain in current directory


# --------------------------------------------- simulation -------------------------------------------------------------

# base command
_simulation_base_command_matrix = {
    "windows": {
        (0, 0): "RunEPlus.bat",
        (8, 2): "energyplus"
    },
    "osx": {
        (0, 0): "runenergyplus",
        (8, 2): "energyplus"
    },
    "linux": {
        (0, 0): "bin/runenergyplus",
        (8, 1): "runenergyplus",
        (8, 4): "energyplus"
    }
}


def get_simulation_base_command():
    commands = _simulation_base_command_matrix[OS_NAME]
    return _get_value_by_version(commands)


# inputs
SIMULATION_INPUT_COMMAND_STYLES = _make_enum(
    "simu_dir",  # {simulation_dir_path}/{simulation_base_name}
    "file_path",  # file_path
)

_simulation_input_command_matrix = {
    "windows": {
        "idf": {
            (0, 0): "simu_dir",
            (8, 1): "file_path"
        },
        "epw": {
            (0, 0): "simu_dir",
            (8, 2): "file_path"
        }

    },
    "osx": {
        "idf": {
            (0, 0): "simu_dir",
            (8, 1): "file_path"
        },
        "epw": {
            (0, 0): "file_path"
        }

    },
    "linux": {
        "idf": {
            (0, 0): "file_path"
        },
        "epw": {
            (0, 0): "file_path"
        }
    }
}


def get_simulation_input_command_style(extension):
    assert extension in ("idf", "epw"), f"unknown extension: {extension}"
    styles = _simulation_input_command_matrix[OS_NAME][extension]
    return _get_value_by_version(styles)


# command style
SIMULATION_COMMAND_STYLES = _make_enum(
    "args",
    "kwargs",
)

_simulation_command_styles_matrix = {
    "windows": {
        (0, 0): "args",
        (8, 2): "kwargs"
    },
    "osx": {
        (0, 0): "args",
        (8, 2): "kwargs"
    },
    "linux": {
        (0, 0): "args",
        (8, 5): "kwargs"
    }
}


def get_simulation_command_style():
    return _get_value_by_version(_simulation_command_styles_matrix[OS_NAME])
