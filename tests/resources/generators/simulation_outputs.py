import os

from oplus import CONF, simulate, Epm, get_eplus_base_dir_path
from tests.util import TESTED_EPLUS_VERSIONS


def one_zone_pre_process(epm):
    # set simulation control
    sc = epm.SimulationControl.one()
    sc.do_zone_sizing_calculation = "Yes"
    sc.do_system_sizing_calculation = "Yes"
    sc.do_plant_sizing_calculation = "Yes"
    sc.run_simulation_for_sizing_periods = "No"
    sc.run_simulation_for_weather_file_run_periods = "Yes"

    # set run period
    rp = epm.RunPeriod.one()
    rp.begin_month = 1
    rp.begin_day_of_month = 1
    rp.end_month = 1
    rp.end_day_of_month = 1

    # set all time steps
    for time_step in ["TimeStep", "Hourly", "Daily", "Monthly", "RunPeriod"]:
        epm.Output_Variable.add({
            0: "*",
            1: "Site Outdoor Air Drybulb Temperature",
            2: time_step
        })


to_simulate = [
    {
        "dir_name": "one_zone_uncontrolled",
        "idf": "1ZoneUncontrolled",
        "epw": "USA_FL_Tampa.Intl.AP.722110_TMY3",
        "pre_process": one_zone_pre_process,
        "extensions": ("eio", "err", "eso", "json"),
    }
]


def generate_outputs():
    for eplus_version in TESTED_EPLUS_VERSIONS:
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
            idf_path = os.path.join(
                get_eplus_base_dir_path(eplus_version),
                "ExampleFiles",
                f"{simulation_case['idf']}.idf"
            )
            epw_path = os.path.join(
                get_eplus_base_dir_path(eplus_version),
                "WeatherData",
                f"{simulation_case['epw']}.epw"
            )

            # prepare idf if needed
            pre_process = simulation_case.get("pre_process")
            if pre_process is not None:
                idf = Epm.load(idf_path)
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

