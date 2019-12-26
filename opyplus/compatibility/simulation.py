import os
from .util import v_lookup, make_enum, OS_NAME, APPS_DIR_PATH, EPLUS_DIR_PATTERN


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


def get_simulation_base_command(version):
    commands = _simulation_base_command_matrix[OS_NAME]
    return v_lookup(version, commands)


# inputs
SIMULATION_INPUT_COMMAND_STYLES = make_enum(
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


def get_simulation_input_command_style(extension, version):
    if extension not in ("idf", "epw"):
        raise ValueError(f"unknown extension: {extension}")
    styles = _simulation_input_command_matrix[OS_NAME][extension]
    return v_lookup(version, styles)


# command style
SIMULATION_COMMAND_STYLES = make_enum(
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


def get_simulation_command_style(version):
    return v_lookup(version, _simulation_command_styles_matrix[OS_NAME])


EPLUS_AVAILABLE_VERSIONS = {}  # {(major, minor): , ...

for file_name in os.listdir(APPS_DIR_PATH):
    match = EPLUS_DIR_PATTERN.search(file_name)
    if match is not None:
        major, minor, patch = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        EPLUS_AVAILABLE_VERSIONS[(major, minor)] = os.path.join(APPS_DIR_PATH, file_name)


def get_eplus_base_dir_path(version):
    _major, _minor, _patch = version
    try:
        return EPLUS_AVAILABLE_VERSIONS[(_major, _minor)]
    except KeyError:
        raise KeyError(
            f"requested EnergyPlus version is not installed ({version}). "
            f"Available versions: {list(sorted(EPLUS_AVAILABLE_VERSIONS))}"
        )
