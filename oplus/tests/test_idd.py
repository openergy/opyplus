import unittest

from oplus.idd import *
from oplus.configuration import CONFIG, paths_d


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)


class IDDTest(unittest.TestCase):
    def test_current_idd(self):
        IDD(path=os.path.join(CONFIG.eplus_base_dir_path, "Energy+.idd"))

    def test_all_idds(self):
        for version, base_dir_path in paths_d.items():
            IDD(path=os.path.join(CONFIG.eplus_base_dir_path, "Energy+.idd"))
            logger.info("Idd version %s tested: ok." % str(version))
