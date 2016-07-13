import datetime as dt
import copy
from threading import Thread
from queue import Queue, Empty
import logging
import subprocess

from oplus import __version__


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


def run_eplus_and_log(cmd_l, cwd=None, logger_name=None, encoding=None):
    logger = logging.getLogger(__name__ if logger_name is None else logger_name)
    encoding = "latin-1" if encoding is None else encoding
    p = subprocess.Popen(cmd_l, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    out_reader = NonBlockingStreamReader(p.stdout)
    err_reader = NonBlockingStreamReader(p.stderr)

    while True:
        out = out_reader.readline(0.1)
        if out is not None:
            logger.info(out.decode(encoding).strip())

        err = err_reader.readline(0.1)
        if err is not None:
            # special EPlus function
            err_s = err.decode(encoding).strip()
            if err_s == "EnergyPlus Completed Successfully.":  # redirect to standard output
                logger.info(err_s)
            else:
                logger.error(err_s)

        if p.poll() is not None:
            break


class NonBlockingStreamReader:
    def __init__(self, stream):
        """
        stream: the stream to read from.
                Usually a process' stdout or stderr.
        """

        self._s = stream
        self._q = Queue()

        def _populate_queue(stream, queue):
            """
            Collect lines from 'stream' and put them in 'quque'.
            """

            while True:
                line = stream.readline()
                if line:
                    queue.put(line)
                else:
                    break

        self._t = Thread(target=_populate_queue, args=(self._s, self._q))
        self._t.daemon = True
        self._t.start()  # start collecting lines from the stream

    def readline(self, timeout=None):
        try:
            return self._q.get(block=timeout is not None, timeout=timeout)
        except Empty:
            return None


def check_cache_is_off(method):
    def wrapper(self, *args, **kwargs):
        assert isinstance(self, Cached), "decorator can only be applied to a method or property of a Cached class"
        if self.is_cached:
            raise CachingNotAllowedError("Must turn off cache to perform action.")
        return method(*args, **kwargs)


def cached(method):
    def wrapper(self, *args, **kwargs):
        assert isinstance(self, Cached), "decorator can only be applied to a method or property of a Cached class"
        if not self.is_cached:
            return method(*args, **kwargs)
        key = (method, args, kwargs)
        if key not in self.cache:
            self.cache[key] = method(*args, **kwargs)
        return self.cache[key]
    return wrapper


class Cached:
    cache = None

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

    # def _cache_get(self, key, variable_callable):
    #     if not self.is_cached:
    #         return variable_callable()
    #     if key in self.cache:
    #         self.cache[key] = variable_callable()
    #     return self.cache[key]