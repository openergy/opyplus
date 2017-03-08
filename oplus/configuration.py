import platform
import re
import os
import logging


class ConfigurationError(Exception):
    pass


logger = logging.getLogger(__name__)


# ------------------------------------------------- DEFAULT VARIABLES --------------------------------------------------
class _Config:
    def __init__(self):
        self.eplus_available_versions = {}  # # {version: base_dir_path, ...
        self.eplus_version = None  # (i1, i2, i3)
        self.encoding = "latin-1"
        self.simulation_base_name = "oplus"
        self.default_write_style = "default write"
        self.default_read_style = None

    @property
    def eplus_base_dir_path(self):
        assert self.eplus_version is not None, "Eplus version must be set."
        assert self.eplus_version in self.eplus_available_versions, "Eplus version was not found in available versions."
        return self.eplus_available_versions[self.eplus_version]

    @property
    def os_name(self):
        global os_name
        return os_name


CONF = _Config()

# --------------------------------------------- END OF DEFAULT VARIABLES -----------------------------------------------

# set operating system
sys_name = platform.system()
if sys_name in ("Windows",):  # windows
    os_name = "windows"
elif sys_name in ("Darwin",):  # mac osx
    os_name = "osx"
elif sys_name in ("Linux", ):  # linux
    os_name = "linux"
else:
    raise ConfigurationError("Unknown platform.system(): '%s'." % sys_name)


# get systems specific configurations
if os_name == "windows":
    apps_dir, pattern = r"C:\\", re.compile("EnergyPlusV(\d*)-(\d*)-(\d*)")
elif os_name == "osx":  # mac osx
    apps_dir, pattern = "/Applications", re.compile("EnergyPlus-(\d*)-(\d*)-(\d*)")
elif os_name == "linux":  # linux
    apps_dir, pattern = "/usr/local", re.compile("EnergyPlus-(\d*)-(\d*)-(\d*)")
else:
    raise ConfigurationError("Unknown os_name: '%s'" % CONF.os_name)

# find most recent version of EnergyPlus
for file_name in os.listdir(apps_dir):
    match = pattern.search(file_name)
    if match is not None:
        version_tuple = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        CONF.eplus_available_versions[version_tuple] = os.path.join(apps_dir, file_name)

if len(CONF.eplus_available_versions) == 0:
    logger.warning("Base directory was not found. You must provide the path with 'set_configuration'.")
else:
    CONF.eplus_version = sorted(CONF.eplus_available_versions.keys(), reverse=True)[0]
    logger.info(
        "EnergyPlus version: '%s', base directory: '%s'. Use 'set_configuration' to change it." %
        (".".join([str(i) for i in CONF.eplus_version]), CONF.eplus_available_versions[CONF.eplus_version]))