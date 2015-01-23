# os_name, eplus_root_dir_path
import platform
import re
import os
import logging
# todo: check that most functionalities work without eplus installed


class ConfigurationError(Exception):
    pass


# ------------------------------------------------- DEFAULT VARIABLES --------------------------------------------------
class _Config:
    def __init__(self):
        self.logger_name = os.environ.get("OPLUS_LOGGER_NAME", "OPlus")
        self.os_name = None
        self.eplus_base_dir_path = None
        self.eplus_version = None  # (i1, i2, i3)
        self.encoding = "latin-1"


CONFIG = _Config()

# --------------------------------------------- END OF DEFAULT VARIABLES -----------------------------------------------

# set operating system
sys_name = platform.system()
if sys_name in ("Windows",):  # windows
    CONFIG.os_name = "windows"
elif sys_name in ("Darwin",):  # mac osx
    CONFIG.os_name = "osx"
elif sys_name in ("Linux", ):  # linux
    CONFIG.os_name = "linux"
else:
    raise ConfigurationError("Unknown platform.system(): '%s'." % sys_name)


# get systems specific configurations
if CONFIG.os_name == "windows":
    apps_dir, pattern = r"C:/", re.compile("EnergyPlusV(\d*)-(\d*)-(\d*)")
elif CONFIG.os_name == "osx":  # mac osx
    apps_dir, pattern = "/Applications", re.compile("EnergyPlus-(\d*)-(\d*)-(\d*)")
elif CONFIG.os_name == "linux":  # linux
    logging.getLogger(CONFIG.logger_name).warning("Default config not implemented for Linux yet. You must provide the "
                                                  "EnergyPlus base path with 'set_configuration'.")

# find most recent version of EnergyPlus
paths_d = {}  # {version_tuple: file_path, ...}
for file_name in os.listdir(apps_dir):
        match = pattern.search(file_name)
        if match is not None:
            version_tuple = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            paths_d[version_tuple] = os.path.join(apps_dir, file_name)

if len(paths_d) == 0:
    logging.getLogger(CONFIG.logger_name).warning(
        "Base directory was not found. You must provide the path with 'set_configuration'.")
else:
    CONFIG.eplus_version = sorted(paths_d, reverse=True)[0]
    CONFIG.eplus_base_dir_path = paths_d[CONFIG.eplus_version]
    logging.getLogger(CONFIG.logger_name).info(
        "EnergyPlus version: '%s', base directory: '%s'. Use 'set_configuration' to change it." %
        (".".join([str(i) for i in CONFIG.eplus_version]), CONFIG.eplus_base_dir_path))


def set_configuration(**kwargs):
    logger = logging.getLogger(CONFIG.logger_name)

    for k, v in kwargs.items():
        if not hasattr(CONFIG, k):
            raise ConfigurationError("Unknown configuration parameter: '%s'." % k)

        if k == "eplus_base_dir_path":
            if not os.path.exists(v):
                raise ConfigurationError("Given directory does not exist: '%s'." % v)

        setattr(CONFIG, k, v)

        logger.info("Configuration variable '%s' has been set to: '%s'." % (k, v))

if __name__ == "__main__":
    set_configuration(eplus_base_dir=r"C:\EnergyPlusV7-2-0")
    print(CONFIG.eplus_base_dir_path)