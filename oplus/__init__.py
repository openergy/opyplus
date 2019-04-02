from .version import version as __version__

from oplus.configuration import CONF
from oplus.epm.api import *
from oplus.weather_data.api import *
from oplus.eio import Eio
from oplus.mtd import Mtd
from oplus.err import Err
from oplus.summary_table import SummaryTable
from oplus.output_table import OutputTable
from oplus.simulation import Simulation, simulate
# from oplus.standard_output import StandardOutputFile

# todo: manage multi-files inputs
# todo: must be able oplus even if eplus is not installed
