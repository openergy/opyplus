import os

from .util import OS_NAME
from ..compatibility import get_eplus_base_dir_path


def get_simulated_epw_path(version):
    """
    Returns
    -------
    None if epw can be anywhere
    """
    from oplus import CONF  # touchy imports

    if OS_NAME == "windows":
        return os.path.join(get_eplus_base_dir_path(version), "WeatherData", "%s.epw" % CONF.default_model_name)

    #  on linux or osx, epw may remain in current directory
