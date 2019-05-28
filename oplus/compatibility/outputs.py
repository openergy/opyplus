from .util import make_enum, v_lookup, OS_NAME

OUTPUT_FILES_LAYOUTS = make_enum(
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


def get_output_files_layout(version, output_category):
    """
    Parameters
    ----------
    output_category: str
        inputs: epw, idf
        table: summary table
        other: other
    """
    # check  category
    if output_category not in ("inputs", "table", "other"):
        raise RuntimeError(f"unknown {output_category}")

    # get version dict
    layouts = _layouts_matrix[OS_NAME][output_category]

    # get version
    return v_lookup(version, layouts)
