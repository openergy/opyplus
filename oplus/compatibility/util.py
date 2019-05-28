import collections
import platform
import re
import os


SYS_NAME = platform.system()
if SYS_NAME in ("Windows",):  # windows
    OS_NAME = "windows"
elif SYS_NAME in ("Darwin",):  # mac osx
    OS_NAME = "osx"
elif SYS_NAME in ("Linux",):  # linux
    OS_NAME = "linux"
else:
    raise RuntimeError("Unknown platform.system(): '%s'." % SYS_NAME)

if OS_NAME == "windows":
    APPS_DIR_PATH, EPLUS_DIR_PATTERN = r"C:\\", re.compile("EnergyPlusV(\d*)-(\d*)-(\d*)")
elif OS_NAME == "osx":  # mac osx
    APPS_DIR_PATH, EPLUS_DIR_PATTERN = "/Applications", re.compile("[eE]nergy[pP]lus-(\d*)[-\.](\d*)[-\.](\d*)")
elif OS_NAME == "linux":  # linux
    # became lowercase and dots for >= 9.0.1
    APPS_DIR_PATH, EPLUS_DIR_PATTERN = "/usr/local", re.compile("[eE]nergy[pP]lus-(\d*)[-\.](\d*)[-\.](\d*)")
else:
    raise RuntimeError("Unknown os_name: '%s'" % OS_NAME)


def v_lookup(version, d):
    """
    Finds the value depending in current eplus version.


    Parameters
    ----------
    version
    d: dict
        {(0, 0): value, (x, x): value, ...}
        for version v, current value is the value of version lv such as lv <= v < lv+1
    """
    from oplus import CONF  # touchy import

    v = version[:2]
    for lv, value in sorted(d.items(), reverse=True):
        if v >= lv:
            return value


def make_enum(*keys):
    Enum = collections.namedtuple("Enum", keys)
    return Enum(**dict([(k, k) for k in keys]))
