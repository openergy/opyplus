import unittest

from oplus.idd import *
from oplus.configuration import CONF


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)


class IDDTest(unittest.TestCase):
    def test_current_idd(self):
        IDD(path=os.path.join(CONF.eplus_base_dir_path, "Energy+.idd"))

    def test_all_idds(self):
        for version, base_dir_path in CONF.eplus_available_versions.items():
            IDD(path=os.path.join(CONF.eplus_base_dir_path, "Energy+.idd"))
            logger.info("Idd version %s tested: ok." % str(version))
