import os

from .util import OS_NAME
from ..compatibility import get_eplus_base_dir_path


def get_simulated_epw_path(version, model_name=None):
    """
    Returns
    -------
    None if epw can be anywhere
    """
    from oplus import CONF  # touchy imports

    model_name = CONF.default_model_name if model_name is None else model_name

    if OS_NAME == "windows":
        return os.path.join(get_eplus_base_dir_path(version), "WeatherData", f"{model_name}.epw")

    #  on linux or osx, epw may remain in current directory
