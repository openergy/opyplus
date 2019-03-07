import os

from oplus import CONF, simulate, Idf
from oplus.tests.util import TESTED_EPLUS_VERSIONS


def one_zone_pre_process(idf):
    # set simulation control
    sc = idf["SimulationControl"].one()
    sc["Do Zone Sizing Calculation"] = "Yes"
    sc["Do System Sizing Calculation"] = "Yes"
    sc["Do Plant Sizing Calculation"] = "Yes"
    sc["Run Simulation for Sizing Periods"] = "No"
    sc["Run Simulation for Weather File Run Periods"] = "Yes"

    # set run period
    rp = idf["RunPeriod"].one()
    rp["Begin Month"] = 1
    rp["Begin Day of Month"] = 1
    rp["End Month"] = 1
    rp["End Day of Month"] = 1

    # set all time steps
    for time_step in ["TimeStep", "Hourly", "Daily", "Monthly", "RunPeriod"]:
        idf.add_records("Output:Variable,*,Site Outdoor Air Drybulb Temperature,%s;" % time_step)


to_simulate = [
    {
        "dir_name": "one_zone_uncontrolled",
        "idf": "1ZoneUncontrolled",
        "epw": "USA_FL_Tampa.Intl.AP.722110_TMY3",
        "pre_process": one_zone_pre_process,
        "extensions": ("eio", "err", "eso"),
    }
]


def generate_outputs():
    for eplus_version in TESTED_EPLUS_VERSIONS:
        # set eplus version
        CONF.eplus_version = eplus_version

        # iter simulation cases
        for simulation_case in to_simulate:

            # building_dir_name
            building_dir_name = simulation_case["dir_name"]

            # prepare base dir
            building_path = os.path.realpath(os.path.join(
                os.path.dirname(__file__),
                "..",
                "simulations-outputs",
                building_dir_name)
            )
            if not os.path.isdir(building_path):
                os.mkdir(building_path)

            # prepare directory name (or skip if exists)
            eplus_version_str = "-".join([str(v) for v in eplus_version])
            dir_path = os.path.join(building_path, eplus_version_str)
            if os.path.isdir(dir_path):
                continue
            os.mkdir(dir_path)

            # set paths
            idf_path = os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", f"{simulation_case['idf']}.idf")
            epw_path = os.path.join(CONF.eplus_base_dir_path, "WeatherData", f"{simulation_case['epw']}.epw")

            # prepare idf if needed
            pre_process = simulation_case.get("pre_process")
            if pre_process is not None:
                idf = Idf(idf_path)
                pre_process(idf)
            else:
                idf = idf_path

            # inform user
            print(eplus_version)
            print(idf_path)
            print(epw_path)
            print("---")

            # simulate
            simulate(idf, epw_path, dir_path)

            # remove unwanted extensions
            for file_name in os.listdir(dir_path):
                file_path = os.path.join(dir_path, file_name)
                _, ext = os.path.splitext(file_path)
                if ext[1:] not in simulation_case["extensions"]:
                    os.remove(file_path)


if __name__ == "__main__":
    generate_outputs()

