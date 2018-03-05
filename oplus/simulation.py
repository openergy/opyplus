"""
Simulation
------------
"""

import os
import shutil
import stat
import logging

from oplus.configuration import CONF
from oplus.util import run_subprocess, Enum, LoggerStreamWriter
from oplus.idf import IDF
from oplus.idd import IDD
from oplus.epw import EPW
from oplus.standard_output import StandardOutputFile
from oplus.mtd import MTD
from oplus.eio import EIO
from oplus.err import ERR
from oplus.summary_table import SummaryTable


DEFAULT_SERVER_PERMS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP


class SimulationError(Exception):
    pass


class WrongExtensionError(SimulationError):
    pass


FILE_REFS = Enum(**dict((ref, ref) for ref in (
    "idf", "epw", "eio", "eso", "mtr", "mtd", "mdd", "err", "summary_table")))


class FileInfo:
    def __init__(self, constructor, get_path):
        self.constructor = constructor
        self.get_path = get_path


def get_input_file_path(dir_path, file_ref):
    assert file_ref in (FILE_REFS.idf, FILE_REFS.epw), "'%s' file ref is not an input file"
    return os.path.join(dir_path, "%s.%s" % (CONF.simulation_base_name, file_ref))


def get_common_output_file_path(dir_path, file_ref):
    assert file_ref in (FILE_REFS.eio, FILE_REFS.eso, FILE_REFS.mtr, FILE_REFS.mtd, FILE_REFS.mdd, FILE_REFS.err), \
        "'%s' file ref is not a common output file"

    if CONF.os_name == "windows":
        if CONF.eplus_version[:2] <= (8, 1):  # todo: check that it is not 8.2 or 8.3
            return os.path.join(dir_path, "%s.%s" % (CONF.simulation_base_name, file_ref))
        else:
            return os.path.join(dir_path, "eplusout.%s" % file_ref)
    elif CONF.os_name == "osx":
        if CONF.eplus_version[:2] <= (8, 1):  # todo: check that it is not 8.2 or 8.3
            return os.path.join(dir_path, "Output", "%s.%s" % (CONF.simulation_base_name, file_ref))
        else:
            if file_ref in ("idf", "epw"):
                return os.path.join(dir_path, "%s.%s" % (CONF.simulation_base_name, file_ref))
            else:
                return os.path.join(dir_path, "eplusout.%s" % file_ref)
    elif CONF.os_name == "linux":
        if CONF.eplus_version[:2] < (8, 5):  # todo: check that it is not 8.2 or 8.3
            return os.path.join(dir_path, "Output", "%s.%s" % (CONF.simulation_base_name, file_ref))
        else:
            return os.path.join(dir_path, "eplusout.%s" % file_ref)
    else:
        raise NotImplementedError("Linux not implemented yet.")


def get_summary_table_file_path(dir_path):
    # TODO: code and test properly
    if CONF.os_name == "windows":
        if CONF.eplus_version[:2] <= (8, 1):  # todo: check that it is not 8.2 or 8.3
            return os.path.join(dir_path, "%sTable.csv" % CONF.simulation_base_name)
        else:
            return os.path.join(dir_path, "eplustbl.csv")
    elif CONF.os_name == "osx":
        if CONF.eplus_version[:2] <= (8, 1):
            return os.path.join(dir_path, "Output", "%sTable.csv" % CONF.simulation_base_name)
        else:
            return os.path.join(dir_path, "eplustbl.csv")

    elif CONF.os_name == "linux":
        if CONF.eplus_version[:2] < (8, 5):
            return os.path.join(dir_path, "Output", "%sTable.csv" % CONF.simulation_base_name)
        else:
            return os.path.join(dir_path, "eplustbl.csv")
    raise NotImplemented()


def _copy_without_read_only(src, dst):
    shutil.copy2(src, dst)
    # ensure not read only
    os.chmod(dst, DEFAULT_SERVER_PERMS)


class Simulation:
    # for subclassing
    _idf_cls = IDF
    _idd_cls = IDD
    _epw_cls = EPW
    _standard_output_file_cls = StandardOutputFile
    _mtd_cls = MTD
    _eio_cls = EIO
    _summary_table_cls = SummaryTable
    _err_cls = ERR

    @classmethod
    def simulate(
            cls,
            idf_or_path,
            epw_or_path,
            base_dir_path,
            simulation_name=None,
            start=None,
            simulation_control=None,
            encoding=None,
            idd_or_path=None,
            stdout=None,
            stderr=None,
            beat_freq=None
    ):
        """
        simulation will be done in os.path.join(base_dir_path, simulation_name) if simulation has a name, else in
            base_dir_path
        default stdout and stderr are logger.info and logger.error
        """
        # manage simulation dir path
        assert os.path.isdir(base_dir_path), "Base dir path not found: '%s'" % base_dir_path
        simulation_dir_path = base_dir_path if simulation_name is None else os.path.join(base_dir_path, simulation_name)

        # make directory if does not exist
        if not os.path.exists(simulation_dir_path):
            os.mkdir(simulation_dir_path)

        # simulation control
        # todo: shouldn't this be in idf builder ?
        if simulation_control is not None:
            _sizing_ = "Sizing"
            _run_periods_ = "RunPeriods"
            if simulation_control not in (_sizing_, _run_periods_):
                raise SimulationError("Unknown simulation_control: '%s'. Must be in : %s." %
                                      (simulation_control, (_sizing_, _run_periods_)))
            if not isinstance(idf_or_path, IDF):
                idf_or_path = IDF(idf_or_path, encoding=encoding, idd_or_path=idd_or_path)

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
        stdout = LoggerStreamWriter(logger_name=__name__, level=logging.INFO) if stdout is None else stdout
        stderr = LoggerStreamWriter(logger_name=__name__, level=logging.ERROR) if stderr is None else stderr
        run_eplus(
            idf_or_path,
            epw_or_path,
            simulation_dir_path,
            stdout=stdout,
            stderr=stderr,
            beat_freq=beat_freq
        )

        # return simulation object
        return cls(
            base_dir_path,
            simulation_name=simulation_name,
            start=start,
            encoding=encoding,
            idd_or_path=idd_or_path
        )

    def __init__(
            self,
            base_dir_path,
            simulation_name=None,
            start=None,
            encoding=None,
            idd_or_path=None
    ):
        self._dir_path = base_dir_path if simulation_name is None else os.path.join(base_dir_path, simulation_name)
        self._start = start
        self._encoding = encoding
        self._idd_or_path = idd_or_path
        self.__idd = None
        self._file_refs = None

        # check simulation directory path exists
        assert os.path.isdir(self._dir_path), "Simulation directory does not exist: '%s'." % self._dir_path

    @property
    def file_refs(self):
        """
        Defined here so that we can use the class variables, in order to subclass in opluslus
        """
        if self._file_refs is None:
            self._file_refs = {
                FILE_REFS.idf: FileInfo(
                    constructor=lambda path: self._idf_cls(path, idd_or_path=self._idd, encoding=self._encoding),
                    get_path=lambda: get_input_file_path(self.dir_path, FILE_REFS.idf)
                ),

                FILE_REFS.epw: FileInfo(
                    constructor=lambda path: self._epw_cls(path, encoding=self._encoding, start=self._start),
                    get_path=lambda: get_input_file_path(self.dir_path, FILE_REFS.epw)
                ),

                FILE_REFS.eio: FileInfo(
                    constructor=lambda path: self._eio_cls(path, encoding=self._encoding),
                    get_path=lambda: get_common_output_file_path(self.dir_path, FILE_REFS.eio)
                ),

                FILE_REFS.eso: FileInfo(
                    constructor=lambda path: self._standard_output_file_cls(
                        path,
                        encoding=self._encoding,
                        start=self._start
                    ),
                    get_path=lambda: get_common_output_file_path(
                        self.dir_path,
                        FILE_REFS.eso
                    )
                ),

                FILE_REFS.mtr: FileInfo(
                    constructor=lambda path: self._standard_output_file_cls(
                        path,
                        encoding=self._encoding,
                        start=self._start),
                    get_path=lambda: get_common_output_file_path(self.dir_path, FILE_REFS.mtr)
                ),

                FILE_REFS.mtd: FileInfo(
                    constructor=lambda path: self._mtd_cls(path, encoding=self._encoding),
                    get_path=lambda: get_common_output_file_path(self.dir_path, FILE_REFS.mtd)
                ),

                FILE_REFS.mdd: FileInfo(
                    constructor=lambda path: open(path, encoding=self._encoding).read(),
                    get_path=lambda: get_common_output_file_path(self.dir_path, FILE_REFS.mdd)

                ),

                FILE_REFS.err: FileInfo(
                    constructor=lambda path: self._err_cls(path, encoding=self._encoding),
                    get_path=lambda: get_common_output_file_path(self.dir_path, FILE_REFS.err)
                ),

                FILE_REFS.summary_table: FileInfo(
                    constructor=lambda path: self._summary_table_cls(path, encoding=self._encoding),
                    get_path=lambda: get_summary_table_file_path(self.dir_path)
                )
            }
        return self._file_refs

    @property
    def dir_path(self):
        return self._dir_path

    @property
    def _idd(self):
        if self.__idd is None:
            self.__idd = IDD.get_idd(self._idd_or_path, encoding=self._encoding)
        return self.__idd

    def _check_file_ref(self, file_ref):
        assert file_ref in self._file_refs, "Unknown extension: '%s'." % file_ref

    def _path(self, file_ref):
        return self.file_refs[file_ref].get_path()

    def exists(self, file_ref):
        assert file_ref in FILE_REFS, \
            "Unknown file_ref: '%s'. Available: '%s'." % (file_ref, list(sorted(FILE_REFS.keys())))
        return os.path.isfile(self._path(file_ref))

    def path(self, file_ref):
        assert self.exists(file_ref), "File '%s' not found in simulation '%s'." % (file_ref, self._path(file_ref))
        return self._path(file_ref)

    def set_start(self, start):
        self._start = start

    def __getattr__(self, item):
        if item not in FILE_REFS:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, item))

        return self.file_refs[item].constructor(self.path(item))


simulate = Simulation.simulate


def run_eplus(idf_or_path, epw_or_path, dir_path, stdout=None, stderr=None, beat_freq=None):
    """
    Parameters
    ----------
    idf_or_path
    epw_or_path
    dir_path
    stdout: default sys.stdout
    stderr: default sys.stderr
    beat_freq: if not none, stdout will be used at least every beat_freq (in seconds)
    """
    # work with absolute paths
    dir_path = os.path.abspath(dir_path)

    # check dir path
    if not os.path.isdir(dir_path):
        raise SimulationError("Simulation directory does not exist: '%s'." % dir_path)

    # save files
    simulation_idf_path = os.path.join(dir_path, CONF.simulation_base_name + ".idf")
    if isinstance(idf_or_path, IDF):
        idf_or_path.save_as(simulation_idf_path)
    else:
        _copy_without_read_only(idf_or_path, simulation_idf_path)

    simulation_epw_path = os.path.join(dir_path, CONF.simulation_base_name + ".epw")
    if isinstance(epw_or_path, EPW):
        epw_or_path.save_as(simulation_epw_path)
    else:
        _copy_without_read_only(epw_or_path, simulation_epw_path)

    # copy epw on windows (on linux or osx, epw may remain in current directory)
    if CONF.os_name == "windows":
        temp_epw_path = os.path.join(CONF.eplus_base_dir_path, "WeatherData", "%s.epw" % CONF.simulation_base_name)
        _copy_without_read_only(simulation_epw_path, temp_epw_path)
    else:
        temp_epw_path = None

    # prepare command
    if CONF.os_name == "windows":
        if CONF.eplus_version[:2] <= (8, 1):  # todo: check that it is not 8.2 or 8.3
            last_name = "RunEPlus.bat"
        else:
            last_name = "energyplus"
    elif CONF.os_name == "osx":
        if CONF.eplus_version[:2] <= (8, 1):  # todo: check that it is not 8.2 or 8.3
            last_name = "runenergyplus"
        else:
            last_name = "energyplus"
    elif CONF.os_name == "linux":
        if CONF.eplus_version[:2] < (8, 1):  # todo: check this limit is right
            last_name = "bin/runenergyplus"
        elif CONF.eplus_version[:2] < (8, 4):  # todo: check this limit is right
            last_name = "runenergyplus"
        else:
            last_name = "energyplus"
    else:
        raise SimulationError("unknown os name: %s" % CONF.os_name)

    eplus_cmd = os.path.join(CONF.eplus_base_dir_path, last_name)

    # idf
    if CONF.os_name == "windows":
        if CONF.eplus_version[:2] <= (8, 1):  # todo: check that it is not 8.2 or 8.3
            idf_file_cmd = os.path.join(dir_path, CONF.simulation_base_name)
        else:
            idf_file_cmd = simulation_idf_path
    elif CONF.os_name == "osx":
        if CONF.eplus_version[:2] <= (8, 1):  # todo: check that it is not 8.2 or 8.3
            idf_file_cmd = os.path.join(dir_path, CONF.simulation_base_name)
        else:
            idf_file_cmd = simulation_idf_path
    elif CONF.os_name == "linux":
        idf_file_cmd = simulation_idf_path
    else:
        raise SimulationError("unknown os name: %s" % CONF.os_name)

    # epw
    if CONF.os_name == "windows":
        if CONF.eplus_version[:2] <= (8, 1):  # todo: check that it is not 8.2 or 8.3
            epw_file_cmd = CONF.simulation_base_name,  # only weather data name
        else:
            epw_file_cmd = simulation_epw_path
    elif CONF.os_name == "osx":
        epw_file_cmd = simulation_epw_path
    elif CONF.os_name == "linux":
        epw_file_cmd = simulation_epw_path
    else:
        raise SimulationError("unknown os name: %s" % CONF.os_name)

    # command list
    if CONF.os_name == "windows":
        if CONF.eplus_version[:2] <= (8, 1):  # todo: check that it is not 8.2 or 8.3
            cmd_l = [eplus_cmd, idf_file_cmd, epw_file_cmd]
        else:
            cmd_l = [eplus_cmd, "-w", epw_file_cmd, "-r", idf_file_cmd]
    elif CONF.os_name == "osx":
        if CONF.eplus_version[:2] <= (8, 1):  # todo: check that it is not 8.2 or 8.3
            cmd_l = [eplus_cmd, idf_file_cmd, epw_file_cmd]
        else:
            cmd_l = [eplus_cmd, "-w", epw_file_cmd, "-r", idf_file_cmd]
    elif CONF.os_name == "linux":
        if CONF.eplus_version[:2] <= (8, 4):  # todo: check that it is not 8.2 or 8.3
            cmd_l = [eplus_cmd, idf_file_cmd, epw_file_cmd]
        else:
            cmd_l = [eplus_cmd, "-w", epw_file_cmd, "-r", idf_file_cmd]
    else:
        raise SimulationError("unknown os name: %s" % CONF.os_name)
    # launch calculation
    run_subprocess(
        cmd_l,
        cwd=dir_path,
        stdout=stdout,
        stderr=stderr,
        beat_freq=beat_freq
    )

    # if needed, we delete temp weather data (only on Windows, see above)
    if (temp_epw_path is not None) and os.path.isfile(temp_epw_path):
        os.remove(os.path.join(temp_epw_path))
