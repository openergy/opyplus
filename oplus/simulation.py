import json
import os
import collections
import logging
import shutil
import stat

from oplus import Epm, WeatherData, CONF
from oplus.util import version_str_to_version, run_subprocess, LoggerStreamWriter, PrintFunctionStreamWriter
from .compatibility import OUTPUT_FILES_LAYOUTS, SIMULATION_INPUT_COMMAND_STYLES, SIMULATION_COMMAND_STYLES, \
    get_output_files_layout, get_simulated_epw_path, get_simulation_base_command, get_simulation_input_command_style, \
    get_simulation_command_style, get_eplus_base_dir_path
from oplus.standard_output.standard_output import StandardOutput
from oplus.mtd import Mtd
from oplus.eio import Eio
from oplus.err import Err
from oplus.summary_table import SummaryTable

DEFAULT_SERVER_PERMS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP

EMPTY = "empty"
RUNNING = "running"
FINISHED = "finished"
FAILED = "failed"

logger = logging.getLogger(__name__)


def _copy_without_read_only(src, dst):
    shutil.copy2(src, dst)
    # ensure not read only
    os.chmod(dst, DEFAULT_SERVER_PERMS)


def _get_done_simulation_status(err_path):
    # todo: improve, see with AL
    with open(err_path) as f:
        content = f.read()
    finished = "EnergyPlus Completed Successfully" in content
    return FINISHED if finished else FAILED


def _get_eplus_version(epm):
    eplus_version_str = epm.Version.one()[0]
    eplus_version = version_str_to_version(eplus_version_str)
    return eplus_version


class Info:
    def __init__(self, status, eplus_version):
        """
        Parameters
        ----------
        status: str
            empty: only input files
            running
            finished
            failed
        eplus_version: tuple
        """
        self._dev_status = status  # empty, running, finished, failed (a simulation necessarily has input files)
        self._dev_eplus_version = eplus_version

    @classmethod
    def from_json(cls, path):
        with open(path) as f:
            json_data = json.load(f)
        eplus_version = tuple(json_data["eplus_version"])
        status = json_data["status"]
        return cls(status, eplus_version)

    @property
    def status(self):
        return self._dev_status

    @property
    def eplus_version(self):
        return self._dev_eplus_version

    def to_json_data(self):
        return collections.OrderedDict((
            ("status", self.status),
            ("eplus_version", self.eplus_version)
        ))

    def to_json(self, path):
        with open(path, "w") as f:
            json.dump(self.to_json_data(), f, indent=4)


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
    EMPTY = EMPTY
    RUNNING = RUNNING
    FINISHED = FINISHED
    FAILED = FAILED

    @classmethod
    def _get_resource_rel_path(cls, ref, version):
        # manage info
        if ref == "info":
            return "#info.json"

        # manage eplus files
        if ref in ("idf", "epw"):
            output_category = "inputs"

        elif ref == "summary_table":
            output_category = "table"

        elif ref in (
                "eio",
                "eso",
                "mtr",
                "mtd",
                "mdd",
                "err"):
            output_category = "other"
        else:
            raise ValueError(f"unknown file_ref: {ref}")

        # get layout
        layout = get_output_files_layout(version, output_category)

        # return path
        rel_path = None
        if layout == OUTPUT_FILES_LAYOUTS.eplusout:
            rel_path = f"eplusout.{ref}"

        if layout == OUTPUT_FILES_LAYOUTS.simu:
            rel_path = f"{CONF.default_model_name}.{ref}"

        if layout == OUTPUT_FILES_LAYOUTS.output_simu:
            rel_path = os.path.join("Output", f"{CONF.default_model_name}.{ref}")

        if layout == OUTPUT_FILES_LAYOUTS.simu_table:
            rel_path = f"{CONF.default_model_name}Table.csv"

        if layout == OUTPUT_FILES_LAYOUTS.output_simu_table:
            rel_path = os.path.join("Output", f"{CONF.default_model_name}Table.csv")

        if layout == OUTPUT_FILES_LAYOUTS.eplustbl:
            rel_path = "eplustbl.csv"

        if rel_path is None:
            raise RuntimeError("unknown ref")

        return rel_path

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
            base_dir_path if simulation_name is None else os.path.join(base_dir_path, simulation_name)
        )

        # check directory exists
        if not os.path.isdir(self._dir_abs_path):
            raise NotADirectoryError(f"simulation directory not found: {self._dir_abs_path}")

        # check info file exists, create it if not
        if not os.path.exists(self.get_resource_path("info")):
            logger.warning(
                "Info file not found (info.json), creating one. "
                "This can happen if simulation was probably not created by oplus.")

            # todo: mutualise with layout code in _get_resource_rel_path
            lookup_paths = [
                os.path.join(self._dir_abs_path, rel_path) for rel_path in (
                    "eplusout.idf",
                    f"{CONF.default_model_name}.idf",
                    os.path.join("Output", f"{CONF.default_model_name}.idf")
            )]
            for path in lookup_paths:
                if os.path.isfile(path):
                    break
            else:
                raise RuntimeError(
                    "idf file not found, can't create simulation object. Looked up paths:\n" +
                    "\n - ".join(lookup_paths)
                )

            # find epm version
            epm = Epm.load(path)
            eplus_version = _get_eplus_version(epm)

            # find simulation status (we can't use get_resource_rel_path because no _info variable yet)
            err_path = os.path.join(self._dir_abs_path, self._get_resource_rel_path("err", eplus_version))
            status = _get_done_simulation_status(err_path)

            # create and dump info
            info = Info(status=status, eplus_version=eplus_version)
            info.to_json(self.get_resource_path("info"))

        # load info file
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
        if isinstance(epm_or_buffer_or_path, Epm):
            epm = epm_or_buffer_or_path
        else:
            epm = Epm.load(epm_or_buffer_or_path)

        # weather data
        if isinstance(weather_data_or_buffer_or_path, WeatherData):
            weather_data = weather_data_or_buffer_or_path
        else:
            weather_data = WeatherData.load(weather_data_or_buffer_or_path)

        # find eplus version
        eplus_version = _get_eplus_version(epm)

        # store inputs
        epm.save(os.path.join(
            dir_path,
            cls._get_resource_rel_path("idf", eplus_version)
        ))
        weather_data.save(os.path.join(
            dir_path,
            cls._get_resource_rel_path("epw", eplus_version)
        ))

        # store info
        info = Info(EMPTY, eplus_version)
        info.to_json(os.path.join(
            dir_path,
            cls._get_resource_rel_path("info", eplus_version)
        ))

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
            _copy_without_read_only(self.get_resource_path("epw"), temp_epw_path)

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
            epw_file_cmd = self._get_resource_rel_path("epw", self._info.eplus_version)
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

        # check if simulation was successful
        status = _get_done_simulation_status(self.get_resource_path("err"))

        # inform new status
        self._info._dev_status = status
        self._info.to_json(self.get_resource_path("info"))

    def get_dir_path(self):
        return self._dir_abs_path

    def get_resource_path(self, ref):
        version = None if ref == "info" else self._info.eplus_version
        return os.path.join(self._dir_abs_path, self._get_resource_rel_path(ref, version))

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

    def get_path(self):
        return self._dir_abs_path

    def get_in_epm(self):
        return Epm.load(self.get_resource_path("idf"))

    def get_in_weather_data(self):
        return WeatherData.load(self.get_resource_path("epw"))

    @check_status(FINISHED, FAILED)
    def get_out_err(self):
        return Err(self.get_resource_path("err"))

    @check_status(FINISHED, FAILED)
    def get_out_epm(self):
        return Epm.load(self.get_resource_path("idf"))

    @check_status(FINISHED, FAILED)
    def get_out_weather_data(self):
        return WeatherData.load(self.get_resource_path("epw"))

    @check_status(FINISHED)
    def get_out_eso(self, print_function=lambda x: None):
        return StandardOutput(self.get_resource_path("eso"), print_function=print_function)

    @check_status(FINISHED)
    def get_out_eio(self):
        return Eio(self.get_resource_path("eio"))

    @check_status(FINISHED)
    def get_out_mtr(self):
        return StandardOutput(self.get_resource_path("mtr"))

    @check_status(FINISHED)
    def get_out_mtd(self):
        return Mtd(self.get_resource_path("mtd"))

    @check_status(FINISHED)
    def get_out_mdd(self):
        with open(self.get_resource_path("mdd")) as f:
            return f.read()

    @check_status(FINISHED)
    def get_out_summary_table(self):
        return SummaryTable(self.get_resource_path("summary_table"))


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
