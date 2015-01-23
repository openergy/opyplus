import os
import tempfile
import shutil

from oplus.configuration import CONFIG
from oplus.util import run_subprocess_and_log
from oplus.idf import IDF
from oplus.idd import IDD
from oplus.epw import EPW
from oplus.standard_output import StandardOutputFile
from oplus.mtd import MTD


class SimulationError(Exception):
    pass

default_logger_name = __name__ if CONFIG.logger_name is None else CONFIG.logger_name


class Simulation:
    # todo: authorize several simulations
    BASE_NAME = "oplus"

    STATUS_WAITING = -1
    STATUS_INITIALIZED = 0
    STATUS_EXITED = 1

    def __init__(self, idf_or_path, epw_or_path, dir_path=None, logger_name=None, encoding=None,
                 idd_or_path=None, start=None):
        self._logger_name = logger_name
        self._encoding = CONFIG.encoding if encoding is None else encoding

        self._idf_or_path = idf_or_path
        self._epw_or_path = epw_or_path
        self._idd_or_path = idd_or_path

        self._start = start

        self._status = self.STATUS_WAITING
        self._dir_path = dir_path

        self._idf = None
        self._epw = None
        self._eso = None
        self._mtr = None
        self._err = None
        self._mtd = None

        # initialize if given directory mode
        if self._dir_path is not None:
            self._initialize()
        self._temp_dir = None

    def _initialize(self):
        if self._status != self.STATUS_WAITING:
            raise SimulationError("Can't initialize twice, create new simulation if needed.")

        if not os.path.isdir(self._dir_path):
            raise SimulationError("Wrong directory path given: '%s'." % self._dir_path)

        # prepare files
        # idf
        if isinstance(self._idf_or_path, str):
            if not os.path.isfile(self._idf_or_path):
                raise SimulationError("No idf file at given path: '%s'." % self._idf_or_path)
            shutil.copy2(self._idf_or_path, self._path("idf"))
        elif isinstance(self._idf_or_path, IDF):
            self._idf_or_path.save_as(self._path("idf"))
        else:
            raise SimulationError("Unknown type for an idf: '%s'." % type(self._idf_or_path))
        # epw
        if isinstance(self._epw_or_path, str):
            if not os.path.isfile(self._epw_or_path):
                raise SimulationError("No epw file at given path: '%s'." % self._epw_or_path)
            shutil.copy2(self._epw_or_path, self._path("epw"))
        elif isinstance(self._epw_or_path, EPW):
            self._epw_or_path.save_as(self._path("epw"))
        else:
            raise SimulationError("Unknown type for an epw: '%s'." % type(self._epw_or_path))

        self._status = self.STATUS_INITIALIZED

        return self

    def __enter__(self):
        if self._dir_path is not None:
            raise SimulationError("Directory path has already been given, tempdir mode is not available anymore.")
        self._temp_dir = tempfile.TemporaryDirectory(prefix="oplus-")  # todo: is never deleted...
        self._dir_path = self._temp_dir.name
        self._initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
        self._dir_path = None
        self._status = self.STATUS_EXITED

    def _path(self, file_ref):
        if file_ref in ("idf", "epw"):  # input files
            return os.path.join(self._dir_path, "%s.%s" % (self.BASE_NAME, file_ref))
        if file_ref in ("eso", "mtr", "eio", "mtd", "err"):
            if CONFIG.os_name == "windows":
                return os.path.join(self._dir_path, "%s.%s" % (self.BASE_NAME, file_ref))
            elif CONFIG.os_name == "osx":
                return os.path.join(self._dir_path, "Output", "%s.%s" % (self.BASE_NAME, file_ref))
            else:
                raise NotImplementedError("Linux not implemented yet.")

        raise SimulationError("Unknown file_ref: '%s'." % file_ref)

    def path(self, file_ref):
        if self._status == self.STATUS_WAITING:
            raise SimulationError("Path doesn't exist yet, enter context manager first.")
        _path = self._path(file_ref)
        if _path is None:
            return None
        if not os.path.isfile(_path):
            return None
        return _path

    def copy(self, file_ref, destination_path):
        source_path = self.path(file_ref)
        if source_path is None:
            raise SimulationError("Requested file does not exist, could not copy (probably due to a simulation error).")
        shutil.copy2(source_path, destination_path)

    def set_start(self, start):
        self._start = start
        if self._eso is not None:
            self._eso.set_start(start)
        if self._mtr is not None:
            self._mtr.set_start(start)

    @property
    def simulation_dir_path(self):
        return self._dir_path

    @property
    def idf(self):
        if self._status == self.STATUS_WAITING:
            raise SimulationError("Can't access idf before Simulation has been entered by the context manager.")
        if self._idf is None:
            # MANAGE IDD
            # no idd
            if self._idd_or_path is None:
                idd = None
            # idd is a path
            elif isinstance(self._idd_or_path, str):
                if not os.path.isfile(self._idd_or_path):
                    raise SimulationError("No idd file at given path: '%s'." % self._idd_or_path)
                idd = IDD(self._idd_or_path)
            # idd is an object
            elif isinstance(self._idd_or_path, IDD):
                idd = self._idd_or_path
            else:
                raise SimulationError("Unknown type for an idd: '%s'." % type(self._idd_or_path))
            # CREATE IDF
            self._idf = IDF(self.path("idf"), idd_or_path=idd, logger_name=self._logger_name, encoding=self._encoding)
        return self._idf

    @property
    def epw(self):
        if self._status == self.STATUS_WAITING:
            return None
        if self._epw is None:
            self._epw = EPW(self.path("epw"), logger_name=self._logger_name, encoding=self._encoding)
        return self._epw

    @property
    def eso(self):
        if self._status == self.STATUS_WAITING:
            return None
        if self._eso is None:
            _path = self.path("eso")
            if _path is None:
                return None
            self._eso = StandardOutputFile(_path, start=self._start, logger_name=self._logger_name,
                                           encoding=self._encoding)
        return self._eso

    @property
    def mtr(self):
        if self._status == self.STATUS_WAITING:
            return None
        if self._mtr is None:
            _path = self.path("mtr")
            if _path is None:
                return None
            self._mtr = StandardOutputFile(_path, start=self._start, logger_name=self._logger_name,
                                           encoding=self._encoding)
        return self._mtr

    @property
    def mtd(self):
        if self._status == self.STATUS_WAITING:
            return None
        if self._mtd is None:
            _path = self.path("mtd")
            if _path is None:
                return None
            self._mtd = MTD(_path, logger_name=self._logger_name, encoding=self._encoding)
        return self._mtd

    @property
    def err(self):
        return self._err

    def run(self, logger_name=None):
        if self._status != self.STATUS_INITIALIZED:
            raise SimulationError("Can't run idf because context manager has not been entered.")

        # run
        self._run_eplus(logger_name=logger_name)

    def size(self, logger_name=None):
        if self._status != self.STATUS_INITIALIZED:
            raise SimulationError("Can't size because context manager has not been entered.")

        # prepare SimulationControl
        sc = self.idf("SimulationControl").one
        sc["Do Zone Sizing Calculation"] = "Yes"
        sc["Do System Sizing Calculation"] = "Yes"
        sc["Do Plant Sizing Calculation"] = "Yes"
        sc["Run Simulation for Sizing Periods"] = "Yes"
        sc["Run Simulation for Weather File Run Periods"] = "No"

        # run
        self._run_eplus(logger_name=logger_name)

    def simulate(self, logger_name=None):
        if self._status != self.STATUS_INITIALIZED:
            raise SimulationError("Can't simulate because context manager has not been entered.")

        # prepare SimulationControl
        sc = self.idf("SimulationControl").one
        sc["Do Zone Sizing Calculation"] = "Yes"
        sc["Do System Sizing Calculation"] = "Yes"
        sc["Do Plant Sizing Calculation"] = "Yes"
        sc["Run Simulation for Sizing Periods"] = "No"
        sc["Run Simulation for Weather File Run Periods"] = "Yes"

        # run
        self._run_eplus(logger_name=logger_name)

    def _run_eplus(self, logger_name=None):
        # PREPARE FILES
        # save files if objects may have been changed
        if self._idf is not None:
            self._idf.save_as(self._path("idf"))
        if self._epw is not None:
            self._epw.save_as(self._path("epw"))
        # initialize output
        self._eso = None
        self._err = None

        # copy epw on windows (on linux or osx, epw may remain in current directory)
        if CONFIG.os_name == "windows":
            temp_epw_path = os.path.join(CONFIG.eplus_base_dir_path, "WeatherData", "%s.epw" % self.BASE_NAME)
            shutil.copy2(self.path("epw"), temp_epw_path)
        else:
            temp_epw_path = None

        # prepare command
        eplus_cmd = {
            "windows": os.path.join(CONFIG.eplus_base_dir_path, "RunEPlus.bat"),
            "osx": os.path.join(CONFIG.eplus_base_dir_path, "runenergyplus"),
            "linux": os.path.join(CONFIG.eplus_base_dir_path, "bin/runenergyplus")
        }[CONFIG.os_name]

        idf_base_name = os.path.join(self._dir_path, self.BASE_NAME)

        epw_file_cmd = {
            "windows": self.BASE_NAME,  # only weather data name
            "osx": self.path("epw"),
            "linux": self.path("epw")
        }[CONFIG.os_name]

        cmd_l = [eplus_cmd, idf_base_name, epw_file_cmd]

        # launch calculation
        run_subprocess_and_log(cmd_l=cmd_l, cwd=self._dir_path, encoding=self._encoding,
                               logger_name=self._logger_name if logger_name is None else logger_name)

        # if needed, we delete temp weather data (only on Windows, see above)
        if temp_epw_path is not None:
            os.remove(os.path.join(temp_epw_path))

        # we save err file (in case we are in a temporary directory)
        self._err = open(self.path("err"), encoding=self._encoding).read()


if __name__ == "__main__":
    s = Simulation(r"C:\EnergyPlusV8-1-0\ExampleFiles\1ZoneEvapCooler.idf",
                   r"C:\Users\Geoffroy\Desktop\eso_perf_test\USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw",
                   dir_path=r"C:\Users\Geoffroy\Desktop\simul_dir")
    import logging
    logging.basicConfig(level=logging.DEBUG)
    # with s:
    s.size(logger_name="MY LOGGER")
    print(s.err)
    eso = s.eso

    print(eso.simulation_df())
