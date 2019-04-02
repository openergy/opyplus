import os
import shutil


class ExternalFile:
    def __init__(self, path):
        self._path = path

    @property
    def path(self):
        return self._path

    def check_file_exists(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"external file not found at given path: {self.path}")

    def copy(self, dir_path, chdir=None):
        # prepare extended dir path
        extended_dir_path = dir_path if chdir is None else os.path.join(chdir, dir_path)

        # prepare file name
        file_name = os.path.basename(self._path)

        # copy
        shutil.copy2(self._path, os.path.join(extended_dir_path, file_name))

        # register new path
        self._path = os.path.join(dir_path, file_name)
