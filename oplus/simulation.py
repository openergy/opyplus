import os
import shutil

from oplus.configuration import CONFIG
from oplus.util import run_subprocess_and_log
from oplus.idf import IDF
from oplus.idd import IDD
from oplus.epw import EPW
from oplus.standard_output import StandardOutputFile
from oplus.mtd import MTD
from oplus.eio import EIO


class SimulationError(Exception):
    pass


class WrongExtensionError(SimulationError):
    pass

default_logger_name = __name__ if CONFIG.logger_name is None else CONFIG.logger_name


def simulate(idf_or_path, epw_or_path, dir_path, start=None, simulation_control=None,
             base_name="oplus", logger_name=None, encoding=None, idd_or_path=None):
    # make directory if doesn't exist
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)

    # simulation control
    if simulation_control is not None:
        _sizing_ = "Sizing"
        _run_periods_ = "RunPeriods"
        if not simulation_control in (_sizing_, _run_periods_):
            raise SimulationError("Unknown simulation_control: '%s' (must be 'sizing' or 'run_periods')." %
                                  simulation_control)
        if not isinstance(idf_or_path, IDF):
            idf_or_path = IDF(idf_or_path, logger_name=logger_name, encoding=encoding, idd_or_path=idd_or_path)

        sc = idf_or_path("SimulationControl").one
        if simulation_control == _sizing_:
            # prepare SimulationControl
            sc["Do Zone Sizing Calculation"] = "Yes"
            sc["Do System Sizing Calculation"] = "Yes"
            sc["Do Plant Sizing Calculation"] = "Yes"
            sc["Run Simulation for Sizing Periods"] = "Yes"
            sc["Run Simulation for Weather File Run Periods"] = "No"
        if simulation_control == _run_periods_:
            sc["Do Zone Sizing Calculation"] = "Yes"
            sc["Do System Sizing Calculation"] = "Yes"
            sc["Do Plant Sizing Calculation"] = "Yes"
            sc["Run Simulation for Sizing Periods"] = "No"
            sc["Run Simulation for Weather File Run Periods"] = "Yes"

    # run simulation
    run_eplus(idf_or_path, epw_or_path, dir_path, base_name=base_name, logger_name=logger_name)

    # return simulation object
    return Simulation(dir_path, start=start, base_name=base_name, logger_name=logger_name, encoding=encoding,
                      idd_or_path=idd_or_path)


class Simulation:
    # for subclassing
    idf_cls = IDF
    idd_cls = IDD
    epw_cls = EPW
    standard_output_file_cls = StandardOutputFile
    mtd_cls = MTD
    eio_cls = EIO
    EXTENSIONS = ("idf", "epw", "eso", "eio", "mdd", "mtr", "mtd", "err")

    def __init__(self, dir_path, start=None, base_name="oplus", logger_name=None, encoding=None, idd_or_path=None):
        if not os.path.isdir(dir_path):
            raise SimulationError("Simulation directory does not exist: '%s'." % dir_path)
        self._dir_path = dir_path
        self._base_name = base_name
        self._start = start
        self._logger_name = logger_name
        self._encoding = encoding
        self._idd_or_path = idd_or_path
        self.__idd = None

    @property
    def dir_path(self):
        return self._dir_path

    @property
    def _idd(self):
        if self._idd is None:
            self.__idd = IDD.get_idd(self._idd_or_path, logger_name=self._logger_name, encoding=self._encoding)
        return self.__idd

    def _check_extension(self, extension):
        if not extension in self.EXTENSIONS:
            raise WrongExtensionError("Unknown extension: '%s'." % extension)

    def _path(self, extension):
        self._check_extension(extension)
        if extension in ("idf", "epw"):  # input files
            return os.path.join(self._dir_path, "%s.%s" % (self._base_name, extension))

        if CONFIG.os_name == "windows":
            return os.path.join(self._dir_path, "%s.%s" % (self._base_name, extension))
        elif CONFIG.os_name == "osx":
            return os.path.join(self._dir_path, "Output", "%s.%s" % (self._base_name, extension))
        else:
            raise NotImplementedError("Linux not implemented yet.")

    def exists(self, extension):
        return os.path.isfile(self._path(extension))

    def path(self, extension):
        if not self.exists(extension):
            raise SimulationError("File '%s' not found in simulation '%s'." % (extension, self._dir_path))
        return self._path(extension)

    def set_start(self, start):
        self._start = start

    def __getattr__(self, item):
        try:
            self._check_extension(item)
        except WrongExtensionError:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, item))

        constructors_d = {
            "idf": lambda path: self.idf_cls(path, idd_or_path=self._idd, logger_name=self._logger_name,
                                             encoding=self._encoding),
            "epw": lambda path: self.epw_cls(path, logger_name=self._logger_name, encoding=self._encoding,
                                             start=self._start),
            "eso": lambda path: self.standard_output_file_cls(path, logger_name=self._logger_name,
                                                              encoding=self._encoding, start=self._start),
            "mtr": lambda path: self.standard_output_file_cls(path, logger_name=self._logger_name,
                                                              encoding=self._encoding, start=self._start),
            "mtd": lambda path: self.mtd_cls(path, logger_name=self._logger_name, encoding=self._encoding),
            "eio": lambda path: self.eio_cls(path, logger_name=self._logger_name, encoding=self._encoding),
            "err": lambda path: open(path, encoding=self._encoding).read()
        }

        return constructors_d[item](self.path(item))


def run_eplus(idf_or_path, epw_or_path, dir_path, base_name="oplus", logger_name=None, encoding=None):
    # check dir path
    if not os.path.isdir(dir_path):
        raise SimulationError("Simulation directory does not exist: '%s'." % dir_path)

    # save files
    simulation_idf_path = os.path.join(dir_path, base_name + ".idf")
    if isinstance(idf_or_path, IDF):
        idf_or_path.save_as(simulation_idf_path)
    else:
        shutil.copy2(idf_or_path, simulation_idf_path)

    simulation_epw_path = os.path.join(dir_path, base_name + ".epw")
    if isinstance(epw_or_path, EPW):
        epw_or_path.save_as(epw_or_path)
    else:
        shutil.copy2(epw_or_path, simulation_epw_path)

    # copy epw on windows (on linux or osx, epw may remain in current directory)
    if CONFIG.os_name == "windows":
        temp_epw_path = os.path.join(CONFIG.eplus_base_dir_path, "WeatherData", "%s.epw" % base_name)
        shutil.copy2(simulation_epw_path, temp_epw_path)
    else:
        temp_epw_path = None

    # prepare command
    # eplus
    eplus_cmd = {
        "windows": os.path.join(CONFIG.eplus_base_dir_path, "RunEPlus.bat"),
        "osx": os.path.join(CONFIG.eplus_base_dir_path, "runenergyplus"),
        "linux": os.path.join(CONFIG.eplus_base_dir_path, "bin/runenergyplus")
    }[CONFIG.os_name]

    # idf
    simulation_idf_base_path = os.path.join(dir_path, base_name)

    # epw
    epw_file_cmd = {
        "windows": base_name,  # only weather data name
        "osx": simulation_epw_path,
        "linux": simulation_epw_path
    }[CONFIG.os_name]

    cmd_l = [eplus_cmd, simulation_idf_base_path, epw_file_cmd]

    # launch calculation
    run_subprocess_and_log(cmd_l=cmd_l, cwd=dir_path, encoding=encoding,
                           logger_name=default_logger_name if logger_name is None else logger_name)

    # if needed, we delete temp weather data (only on Windows, see above)
    if temp_epw_path is not None:
        os.remove(os.path.join(temp_epw_path))