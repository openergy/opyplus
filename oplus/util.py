import datetime as dt
import copy
import logging
import subprocess
import collections
import os
import io
import sys
import threading
import contextlib


from oplus import __version__, CONF


logger = logging.getLogger(__name__)


class UtilError(Exception):
    pass


class CachingNotAllowedError(Exception):
    pass


def get_copyright_comment(multi_lines=True):
    if multi_lines:
#         return """----------------------------------------------------------------------------------------
#  |----| |----| |      |    |  |----|      Generated by OPlus version %s.
#  |    | |    | |      |    |  |           Copyright (c) %s, Openergy development team
#  |    | |----| |      |    |  |----|      http://www.openergy.fr
#  |    | |      |      |    |       |      https://github.com/Openergy/oplus
#  |----| |      |----| |----|  |----|
# ----------------------------------------------------------------------------------------
#
# """
        return """----------------------------------------------------------------------------------------
 Generated by OPlus version %s.
 Copyright (c) %s, Openergy development team
 http://www.openergy.fr
 https://github.com/Openergy/oplus
----------------------------------------------------------------------------------------

""" % (__version__, dt.datetime.now().year)
    return "-- OPlus version %s, copyright (c) %s, Openergy development team --" % (__version__, dt.datetime.now().year)


class EPlusDt:
    MONTH = 0
    DAY = 1
    HOUR = 2
    MINUTE = 3

    @classmethod
    def from_datetime(cls, datetime):
        if datetime.minute == 0:
            datetime -= dt.timedelta(hours=1)
            minute = 60
        else:
            minute = datetime.minute

        return cls(datetime.month, datetime.day, datetime.hour + 1, minute)

    @classmethod
    def to_datetime(cls, year, month, day, eplus_hour, eplus_minute):
        """
        Arguments
        ---------
        month
        day
        hour (1 -> 24) => one hour shift
        minute (1 -> 60) => no shift, but 0 is 60 one hour before. We tolerate minute=0 even though eplus does not
            seem to use it.
        """
        hour_cor = 0
        if eplus_minute == 60:
            minute = 0
            hour_cor = 1
        else:
            minute = eplus_minute

        try:
            my_dt = (dt.datetime(year, month, day, eplus_hour-1, minute) +
                     dt.timedelta(hours=hour_cor)).replace(year=year)  # we replace year for one case: y-12-31-24-60
            my_dt.replace(year=year)  # we replace in case timedelta operation impacted year
        except ValueError as e:
            if (month, day) == (2, 29):
                raise UtilError("%s (probable leap year problem: year=%s, month=%s, day=%s)" % (e, year, month, day))
            raise e

        return my_dt

    def __init__(self, month, day, out_hour, out_minute):
        """
        Arguments
        ---------
        month
        day
        hour (1 -> 24) => one hour shift
        minute (1 -> 60) => no shift, but 0 is 60 one hour before. We tolerate minute=0 even though eplus does not
        # todo: unify hour/minute convention, if possible
            seem to use it.
        """
        self._standard_dt = self.to_datetime(2000, month, day, out_hour, out_minute)  # 2000 is a leap year

        # create and store value
        _datetime = copy.copy(self._standard_dt)
        if self._standard_dt.minute == 0:
            _datetime -= dt.timedelta(hours=1)
            minute = 60
        else:
            minute = _datetime.minute

        self._value = _datetime.month, _datetime.day, _datetime.hour + 1, minute

    def __lt__(self, other):
        return self.standard_dt < other.standard_dt

    def __le__(self, other):
        return self.standard_dt <= other.standard_dt

    def __eq__(self, other):
        return self.standard_dt == other.standard_dt

    def __ne__(self, other):
        return self.standard_dt != other.standard_dt

    def __gt__(self, other):
        return self.standard_dt > other.standard_dt

    def __ge__(self, other):
        return self.standard_dt >= other.standard_dt

    def __repr__(self):
        return "<eplus_dt: month=%s, day=%s, hour=%s, minute=%s>" % self._value

    def datetime(self, year):
        return self.to_datetime(year, self._value[self.MONTH], self._value[self.DAY],
                                self._value[self.HOUR], self._value[self.MINUTE])

    @property
    def month(self):
        return self._value[self.MONTH]

    @property
    def day(self):
        return self._value[self.DAY]

    @property
    def hour(self):
        return self._value[self.HOUR]

    @property
    def minute(self):
        return self._value[self.MINUTE]

    @property
    def standard_dt(self):
        return self._standard_dt


def get_start_dt(start):
    """
    Transforms start in start_dt.

    Arguments
    ---------
    start: year num, or date, or datetime
    """
    if isinstance(start, dt.datetime):  # must first test datetime because date is datetime...
        start_dt = start
    elif isinstance(start, dt.date):
        start_dt = dt.datetime(start.year, start.month, start.day)
    elif isinstance(start, int):
        start_dt = dt.datetime(start, 1, 1)
    else:
        raise UtilError("Unknown start type: '%s'." % type(start))
    return start_dt


def _redirect_stream(src, dst, stop_event, freq):
    while not stop_event.is_set():  # read all filled lines
        content = src.readline()
        if content == "":  # empty: break
            break
        dst.write(content)
        if hasattr(dst, "flush"):
            dst.flush()


@contextlib.contextmanager
def redirect_stream(src, dst, freq=0.1):
    stop_event = threading.Event()
    t = threading.Thread(target=_redirect_stream, args=(src, dst, stop_event, freq))
    t.daemon = True
    t.start()
    try:
        yield
    finally:
        stop_event.set()
        t.join()


class LoggerStreamWriter:
    def __init__(self, logger_name, level):
        self._logger = logging.getLogger(logger_name)
        self._level = level

    def write(self, message):
        message = message.strip()
        if message != "":
            self._logger.log(self._level, message)


def run_subprocess(command, cwd=None, stdout=None, stderr=None, shell=False, beat_freq=None):
    """
    Parameters
    ----------
    command: command
    cwd: current working directory
    stdout: output info stream (must have 'write' method)
    stderr: output error stream (must have 'write' method)
    shell: see subprocess.Popen
    beat_freq: if not none, stdout will be used at least every beat_freq (in seconds)
    """
    # prepare variables
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    # run subprocess
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        shell=shell,
        universal_newlines=True
    ) as sub_p:
        # link output streams
        with redirect_stream(sub_p.stdout, stdout), redirect_stream(sub_p.stderr, stderr):
            while True:
                try:
                    sub_p.wait(timeout=beat_freq)
                    break
                except subprocess.TimeoutExpired:
                    stdout.write("subprocess is still running\n")
                    if hasattr(sys.stdout, "flush"):
                        sys.stdout.flush()
        return sub_p.returncode


class CacheKey:
    """
    emulated a dict that can store hashable types
    """
    def __init__(self, method, *args, **kwargs):
        self._value = tuple([method] + list(args) + [(k, v) for k, v in sorted(kwargs.items())])

    def __hash__(self):
        return self._value.__hash__()

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __str__(self):
        return "<CacheKey: %s>" % str(self._value)


def check_cache_is_off(method):
    def wrapper(self, *args, **kwargs):
        assert isinstance(self, Cached), "decorator was applied to a non-cached class (%s)" % method
        if self.is_cached:
            raise CachingNotAllowedError("Must turn off cache to perform action.")
        return method(self, *args, **kwargs)
    return wrapper


def cached(method):
    def wrapper(self, *args, **kwargs):
        assert isinstance(self, Cached), "decorator was applied to a non-cached class (%s)" % method
        if not self.is_cached:
            return method(self, *args, **kwargs)
        key = CacheKey(method, *args, **kwargs)
        if key not in self.cache:
            self.cache[key] = dict(value=method(self, *args, **kwargs), hits=0)
        else:
            self.cache[key]["hits"] += 1
        return self.cache[key]["value"]
    return wrapper


class Cached:
    cache = None  # dict(key: dict(value=v, hits=0))  (hits for testing)

    def activate_cache(self):
        if self.cache is None:
            self.cache = {}

    def deactivate_cache(self):
        self.cache = None

    def clear_cache(self):
        if self.cache is not None:
            self.cache = {}

    @property
    def is_cached(self):
        return self.cache is not None


class Enum(collections.UserDict):
    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, key, value):
        # we bypass 'data' (used by parent class) and all private keys (in case used by parent class)
        if (key == "data") or (key[0] == "_"):
            super().__setattr__(key, value)
        self[key] = value


def get_string_buffer(path_or_content, expected_extension, encoding):
    """
    path_or_content: path or content_str or content_bts or string_io or bytes_io

    Returns
    -------
    string_buffer, path

    path will be None if input was not a path
    """
    buffer, path = None, None

    # path or content string

    if isinstance(path_or_content, str):
        if path_or_content[-len(expected_extension)-1:] == ".%s" % expected_extension:
            assert os.path.isfile(path_or_content), "No file at given path: '%s'." % path_or_content
            buffer, path = open(path_or_content, encoding=encoding), path_or_content
        else:
            buffer = io.StringIO(path_or_content, )

    # text io
    elif isinstance(path_or_content, io.TextIOBase):
        buffer = path_or_content

    # bytes
    elif isinstance(path_or_content, bytes):
        buffer = io.StringIO(path_or_content.decode(encoding=encoding))
    elif isinstance(path_or_content, io.BufferedIOBase):
        buffer = io.StringIO(path_or_content.read().decode(encoding=encoding))
    else:
        raise UtilError("path_or_content type could not be identified")

    return buffer, path
