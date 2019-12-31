"""Functions for epw compatibility between E+ versions and platforms."""
import os

from opyplus import CONF
from .util import OS_NAME
from ..compatibility import get_eplus_base_dir_path


def get_simulated_epw_path(version):
    """
    Get simulated epw path depending on E+.

    Parameters
    ----------
    version: tuple of int

    Returns
    -------
    str or None
        None if epw can be anywhere
    """
    if OS_NAME == "windows":
        return os.path.join(get_eplus_base_dir_path(version), "WeatherData", "%s.epw" % CONF.default_model_name)

    #  on linux or osx, epw may remain in current directory
