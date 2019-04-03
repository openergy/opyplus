import os

from .compatibility import APPS_DIR_PATH, EPLUS_DIR_PATTERN


# ------------------------------------------------- DEFAULT VARIABLES --------------------------------------------------
class _Conf:
    encoding = "latin-1"  # even needed for example files...
    simulation_base_name = "oplus"
    external_files_suffix = "-external"
    
    def __init__(self):
        self.eplus_available_versions = {}  # {version: base_dir_path, ...
        self._eplus_version = None  # (i1, i2, i3)

        # set available versions
        self._set_available_versions()

    def _set_available_versions(self):
        # find most recent version of EnergyPlus
        for file_name in os.listdir(APPS_DIR_PATH):
            match = EPLUS_DIR_PATTERN.search(file_name)
            if match is not None:
                version_tuple = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
                self.eplus_available_versions[version_tuple] = os.path.join(APPS_DIR_PATH, file_name)

    @property
    def eplus_version(self):
        """
        if _eplus_version is defined => _eplus_version
        else most recent eplus available version
        """
        # check energy plus is installed
        if len(self.eplus_available_versions) == 0:
            raise RuntimeError("Energy plus is not install, can't use oplus package.")

        # see if version is defined
        if self._eplus_version is not None:
            return self._eplus_version

        # return most recent version
        return sorted(self.eplus_available_versions.keys(), reverse=True)[0]

    @eplus_version.setter
    def eplus_version(self, value):
        # check version is available
        if value not in self.eplus_available_versions:
            raise RuntimeError(f"Eplus version {value} was not found in available versions.")

        # set
        self._eplus_version = value

    @property
    def eplus_base_dir_path(self):
        return self.eplus_available_versions[self.eplus_version]


CONF = _Conf()
