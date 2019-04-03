from .util import get_value_by_version, make_enum, OS_NAME

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
    return get_value_by_version(commands)


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


def get_simulation_input_command_style(extension):
    if extension not in ("idf", "epw"):
        raise ValueError(f"unknown extension: {extension}")
    styles = _simulation_input_command_matrix[OS_NAME][extension]
    return get_value_by_version(styles)


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


def get_simulation_command_style():
    return get_value_by_version(_simulation_command_styles_matrix[OS_NAME])
