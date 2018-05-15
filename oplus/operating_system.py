import platform
import re


# set operating system
SYS_NAME = platform.system()
if SYS_NAME in ("Windows",):  # windows
    OS_NAME = "windows"
elif SYS_NAME in ("Darwin",):  # mac osx
    OS_NAME = "osx"
elif SYS_NAME in ("Linux",):  # linux
    OS_NAME = "linux"
else:
    raise RuntimeError("Unknown platform.system(): '%s'." % SYS_NAME)


# get systems specific configurations
if OS_NAME == "windows":
    APPS_DIR_PATH, EPLUS_DIR_PATTERN = r"C:\\", re.compile("EnergyPlusV(\d*)-(\d*)-(\d*)")
elif OS_NAME == "osx":  # mac osx
    APPS_DIR_PATH, EPLUS_DIR_PATTERN = "/Applications", re.compile("EnergyPlus-(\d*)-(\d*)-(\d*)")
elif OS_NAME == "linux":  # linux
    APPS_DIR_PATH, EPLUS_DIR_PATTERN = "/usr/local", re.compile("EnergyPlus-(\d*)-(\d*)-(\d*)")
else:
    raise RuntimeError("Unknown os_name: '%s'" % OS_NAME)



