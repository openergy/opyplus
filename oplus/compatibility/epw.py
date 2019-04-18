import os

from .util import OS_NAME


def get_simulated_epw_path():
    """
    Returns
    -------
    None if epw can be anywhere
    """
    from oplus import CONF  # touchy imports

    if OS_NAME == "windows":
        return os.path.join(CONF.eplus_base_dir_path, "WeatherData", "%s.epw" % CONF.default_model_name)

    #  on linux or osx, epw may remain in current directory
