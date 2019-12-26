import os
import logging
import shutil

from opyplus import Epm, WeatherData, CONF
from opyplus.util import version_str_to_version, run_subprocess, LoggerStreamWriter, PrintFunctionStreamWriter
from ..compatibility import SIMULATION_INPUT_COMMAND_STYLES, SIMULATION_COMMAND_STYLES, \
    get_simulated_epw_path, get_simulation_base_command, get_simulation_input_command_style, \
    get_simulation_command_style, get_eplus_base_dir_path

from opyplus.standard_output.standard_output import StandardOutput
from opyplus.mtd import Mtd
from opyplus.eio import Eio
from opyplus.err import Err
from opyplus.summary_table import SummaryTable
from .info import Info
from .resources import ResourcesRefs, create_resources_map, get_opyplus_path

EMPTY = "empty"
RUNNING = "running"
FINISHED = "finished"
FAILED = "failed"

logger = logging.getLogger(__name__)


def check_status(*authorized):
    def method_generator(method):
        def new_method(self, *args, **kwargs):
            if self.get_status() not in authorized:
                raise RuntimeError(
                    f"current status: '{self.get_status()}', can't call method (authorized statuses: {authorized}"
                )
            return method(self, *args, **kwargs)

        return new_method

    return method_generator


class Simulation:
    """
    Simulation output data has following characteristics:
    - convention: left (00:00 is [00:00;01:00[ for an hourly series)
    - clock: tzt

    Left convention applies to datetime index. In data columns, start and end of period are given (=> user can choose to
    work with one convention or another).
    """
    _info = None
    _resource_map = None

    EMPTY = EMPTY
    RUNNING = RUNNING
    FINISHED = FINISHED
    FAILED = FAILED

    @classmethod
    def get_simulation_dir_path(cls, base_dir_path, simulation_name=None):
        return base_dir_path if simulation_name is None else os.path.join(base_dir_path, simulation_name)

    def __init__(self, base_dir_path, simulation_name=None):
        """
        Parameters
        ----------
        base_dir_path: simulation dir path
        simulation_name: str, default None
            if provided, simulation will be looked for in {base_dir_path}/{simulation_name}
            else, simulation will be looked for in {base_dir_path}

        A simulation is not characterized by it's input files but by it's base_dir_path. This approach makes it
        possible to load an already simulated directory without having to define it's idf or epw.
        """
        # store absolute: important for eplus commands
        self._dir_abs_path = os.path.abspath(
            self.get_simulation_dir_path(base_dir_path, simulation_name=simulation_name)
        )

        # check directory exists
        if not os.path.isdir(self._dir_abs_path):
            raise NotADirectoryError(f"simulation directory not found: {self._dir_abs_path}")

        # update resource map
        self._update_resource_map()

        # check info file exists, create it if not
        if self.get_resource_path(ResourcesRefs.info) is None:
            logger.warning(
                "Info file not found (#info.json), creating one. "
                "This can happen if simulation was not created by opyplus.")

            # find idf
            idf_path = self.get_resource_path(ResourcesRefs.idf)
            if idf_path is None:
                raise FileNotFoundError("Idf file not found, can't create simulation object.")

            # find epm version
            epm = Epm.load(idf_path)
            eplus_version = _get_eplus_version(epm)

            # find simulation status (we can't use get_resource_rel_path because no _info variable yet)
            err_path = self.get_resource_path(ResourcesRefs.err)
            if err_path is None:
                status = EMPTY
            else:
                err_path = os.path.join(self._dir_abs_path, err_path)
                status = _get_done_simulation_status(err_path)

            # create and dump info
            info = Info(status=status, eplus_version=eplus_version)
            info.to_json(get_opyplus_path(self._dir_abs_path, ResourcesRefs.info))

            # reload map
            self._update_resource_map()

        # load info file
        self._load_info()

    def _update_resource_map(self):
        self._resource_map = create_resources_map(self._dir_abs_path)

    def _load_info(self):
        self._info = Info.from_json(self.get_resource_path("info"))

    # ------------------------------------ public api ------------------------------------------------------------------
    @classmethod
    def from_inputs(cls, base_dir_path, epm_or_buffer_or_path, weather_data_or_buffer_or_path, simulation_name=None):
        # create dir if needed
        dir_path = base_dir_path if simulation_name is None else os.path.join(base_dir_path, simulation_name)
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)

        # check empty
        if len(os.listdir(dir_path)) > 0:
            logger.warning(f"called Simulation.from_input on a simulation directory that is not empty ({dir_path})")

        # epm
        epm_path_was_given = False
        if isinstance(epm_or_buffer_or_path, Epm):
            epm = epm_or_buffer_or_path
        else:
            if isinstance(epm_or_buffer_or_path, str) and os.path.isfile(epm_or_buffer_or_path):
                epm_path_was_given = True
            epm = Epm.load(epm_or_buffer_or_path)  # we load epm (even if we will copy input file) to read e+ version

        # weather data
        weather_data, weather_data_path_was_given = None, False
        if isinstance(weather_data_or_buffer_or_path, WeatherData):
            weather_data = weather_data_or_buffer_or_path
        elif isinstance(weather_data_or_buffer_or_path, str) and os.path.isfile(weather_data_or_buffer_or_path):
            weather_data_path_was_given = True
        else:
            weather_data = WeatherData.load(weather_data_or_buffer_or_path)

        # find eplus version
        eplus_version = _get_eplus_version(epm)

        # store simulation inputs
        # idf
        simulation_epm_path = get_opyplus_path(dir_path, ResourcesRefs.idf)
        if epm_path_was_given:
            shutil.copy2(epm_or_buffer_or_path, simulation_epm_path)
        else:
            epm.save(simulation_epm_path)
        # epw
        simulation_weather_data_path = get_opyplus_path(dir_path, ResourcesRefs.epw)
        if weather_data_path_was_given:
            shutil.copy2(weather_data_or_buffer_or_path, simulation_weather_data_path)
        else:
            weather_data.save(simulation_weather_data_path)

        # store info
        info = Info(EMPTY, eplus_version)
        info.to_json(get_opyplus_path(dir_path, ResourcesRefs.info))

        # create and return simulation
        return cls(base_dir_path, simulation_name=simulation_name)

    @check_status(EMPTY)
    def simulate(self, print_function=None, beat_freq=None):
        # manage defaults
        if print_function is not None:
            std_out_err = PrintFunctionStreamWriter(print_function)
        else:
            std_out_err = LoggerStreamWriter(logger_name=__name__, level=logging.INFO)

        # prepare useful variables
        version = self._info.eplus_version

        # inform running
        self._info._dev_status = RUNNING
        self._info.to_json(self.get_resource_path("info"))

        # copy epw if needed (depends on os/eplus version)
        temp_epw_path = get_simulated_epw_path(version)
        if temp_epw_path is not None:
            shutil.copy2(self.get_resource_path("epw"), temp_epw_path)

        # prepare command
        eplus_relative_cmd = get_simulation_base_command(version)
        eplus_cmd = os.path.join(get_eplus_base_dir_path(version), eplus_relative_cmd)

        # idf
        idf_command_style = get_simulation_input_command_style("idf", version)
        if idf_command_style == SIMULATION_INPUT_COMMAND_STYLES.simu_dir:
            idf_file_cmd = os.path.join(self._dir_abs_path, CONF.default_model_name)
        elif idf_command_style == SIMULATION_INPUT_COMMAND_STYLES.file_path:
            idf_file_cmd = self.get_resource_path("idf")
        else:
            raise AssertionError("should not be here")

        # epw
        epw_command_style = get_simulation_input_command_style("epw", version)
        if epw_command_style == SIMULATION_INPUT_COMMAND_STYLES.simu_dir:
            epw_file_cmd = os.path.join(self._dir_abs_path, CONF.default_model_name)
        elif epw_command_style == SIMULATION_INPUT_COMMAND_STYLES.file_path:
            epw_file_cmd = self._resource_map[ResourcesRefs.epw]  # we use rel path
        else:
            raise AssertionError("should not be here")

        # command list
        simulation_command_style = get_simulation_command_style(version)
        if simulation_command_style == SIMULATION_COMMAND_STYLES.args:
            cmd_l = [eplus_cmd, idf_file_cmd, epw_file_cmd]
        elif simulation_command_style == SIMULATION_COMMAND_STYLES.kwargs:
            cmd_l = [eplus_cmd, "-w", epw_file_cmd, "-r", idf_file_cmd]
        else:
            raise RuntimeError("should not be here")

        # launch calculation
        run_subprocess(
            cmd_l,
            cwd=self._dir_abs_path,
            stdout=std_out_err,
            stderr=std_out_err,
            beat_freq=beat_freq
        )

        # if needed, we delete temp weather data (only on Windows, see above)
        if (temp_epw_path is not None) and os.path.isfile(temp_epw_path):
            os.remove(os.path.join(temp_epw_path))

        # update resource map
        self._update_resource_map()

        # check if simulation was successful
        status = _get_done_simulation_status(self.get_resource_path("err"))

        # inform new status
        self._info._dev_status = status
        self._info.to_json(self.get_resource_path("info"))

    def get_dir_path(self):
        return self._dir_abs_path

    def get_resource_path(self, ref, raise_if_not_found=False):
        rel_path = self._resource_map[ref]
        if rel_path is None:
            if raise_if_not_found:
                raise FileNotFoundError(f"requested resource '{ref}' not found")
            return None
        return os.path.join(self._dir_abs_path, rel_path)

    def check_exists(self, ref):
        return os.path.exists(self.get_resource_path(ref))

    def get_status(self):
        """
        Returns
        -------
        empty, success, error
        """
        return self._info.status

    def get_info(self):
        return self._info

    def get_in_epm(self):
        return Epm.load(self.get_resource_path(ResourcesRefs.idf))

    def get_in_weather_data(self):
        return WeatherData.load(self.get_resource_path(ResourcesRefs.epw))

    @check_status(FINISHED, FAILED)
    def get_out_err(self):
        return Err(self.get_resource_path(ResourcesRefs.err, raise_if_not_found=True))

    @check_status(FINISHED, FAILED)
    def get_out_epm(self):
        return Epm.load(self.get_resource_path(ResourcesRefs.idf, raise_if_not_found=True))

    @check_status(FINISHED, FAILED)
    def get_out_weather_data(self):
        return WeatherData.load(self.get_resource_path(ResourcesRefs.epw, raise_if_not_found=True))

    @check_status(FINISHED)
    def get_out_eso(self, print_function=lambda x: None):
        return StandardOutput(
            self.get_resource_path(ResourcesRefs.eso, raise_if_not_found=True),
            print_function=print_function
        )

    @check_status(FINISHED)
    def get_out_eio(self):
        return Eio(self.get_resource_path(ResourcesRefs.eio, raise_if_not_found=True))

    @check_status(FINISHED)
    def get_out_mtr(self):
        return StandardOutput(self.get_resource_path(ResourcesRefs.mtr, raise_if_not_found=True))

    @check_status(FINISHED)
    def get_out_mtd(self):
        return Mtd(self.get_resource_path(ResourcesRefs.mtd, raise_if_not_found=True))

    @check_status(FINISHED)
    def get_out_mdd(self):
        with open(self.get_resource_path(ResourcesRefs.mdd, raise_if_not_found=True)) as f:
            return f.read()

    @check_status(FINISHED)
    def get_out_summary_table(self):
        return SummaryTable(self.get_resource_path(ResourcesRefs.summary_table, raise_if_not_found=True))


def simulate(
        epm_or_buffer_or_path,
        weather_data_or_buffer_or_path,
        base_dir_path,
        simulation_name=None,
        print_function=None,
        beat_freq=None
):
    """
    Parameters
    ----------
    epm_or_buffer_or_path
    weather_data_or_buffer_or_path
    base_dir_path: simulation dir path
    simulation_name: str, default None
        if provided, simulation will be done in {base_dir_path}/{simulation_name}
        else, simulation will be done in {base_dir_path}
    print_function:
        interface fct(message): do what you want with message
    beat_freq: float, default None
        if provided, subprocess in which EnergyPlus is run will write at given frequency in standard output. May
        be used to monitor subprocess state.

    Returns
    -------
    Simulation instance
    """
    # create simulation from input
    s = Simulation.from_inputs(
        base_dir_path,
        epm_or_buffer_or_path,
        weather_data_or_buffer_or_path,
        simulation_name=simulation_name
    )

    # simulate
    s.simulate(print_function=print_function, beat_freq=beat_freq)

    # return
    return s


def _get_done_simulation_status(err_path):
    # todo: [GL] [AL] improve
    with open(err_path) as f:
        content = f.read()
    finished = "EnergyPlus Completed Successfully" in content
    return FINISHED if finished else FAILED


def _get_eplus_version(epm):
    eplus_version_str = epm.Version.one()[0]
    eplus_version = version_str_to_version(eplus_version_str)
    return eplus_version
