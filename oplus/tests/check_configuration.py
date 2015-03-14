import logging
import os

logging.basicConfig(level=logging.DEBUG)

logger_name = "test_configuration"


# ------------ CUSTOM LOGIN
if True:  # check custom login
    os.environ["OPLUS_LOGGER_NAME"] = logger_name

from oplus.configuration import set_configuration
from oplus.idd import IDD

# ------------ EPLUS_BASE_DIR
# check current idd
idd = IDD()
print(idd.path)
set_configuration(eplus_base_dir_path=r"C:\EnergyPlusV7-2-0")
idd = IDD()
print(idd.path)

# ------------ LOGGER
set_configuration(logger_name="test_configuration-2")


# ------------ ENCODING
set_configuration(encoding="latin-1")