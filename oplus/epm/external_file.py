import os
import shutil


def ensure_abs_path(path, root_dir_path=None):
    if os.path.isabs(path):
        return os.path.normpath(path)
    elif root_dir_path is None:
        return os.path.normpath(os.path.join(os.getcwd(), path))
    if not os.path.isabs(root_dir_path):
        root_dir_path = os.path.join(os.getcwd(), root_dir_path)
    return os.path.normpath(os.path.join(root_dir_path, path))


class ExternalFile:
    def __init__(self, path):
        """
        Parameters
        ----------
        path: may be relative or absolute
        """
        self._initial_path = path  # !! becomes obsolete at activation
        self._abs_path = None

    def __repr__(self):
        return f"<ExternalFile: {self._abs_path}>"

    def activate(self, model_file_path):
        self._abs_path = ensure_abs_path(self._initial_path, os.path.dirname(model_file_path))

    def get_path(self, mode=None, model_file_path=None):
        """
        Parameters
        ----------
        mode: str, default 'relative'
            'relative', 'absolute'
        model_file_path
        """
        if mode is None:
            mode = "relative"

        if mode == "relative":
            if model_file_path is None:
                model_abs_dir_path = os.getcwd()
            else:
                model_abs_dir_path = os.path.dirname(ensure_abs_path(model_file_path))
            return os.path.relpath(self._abs_path, model_abs_dir_path)

        elif mode == "absolute":
            return self._abs_path

        raise ValueError(f"unknown mode: '{mode}'")

    def check_file_exists(self):
        if not os.path.exists(self._abs_path):
            raise FileNotFoundError(f"external file not found at given path: {self._abs_path}")

    def transfer(self, dir_path, mode="copy", raise_if_not_found=True):
        # ensure absolute
        dir_path = ensure_abs_path(dir_path)

        # manage if file does not exist
        exists = os.path.isfile(self._abs_path)
        if not exists:
            if raise_if_not_found:
                raise FileNotFoundError(f"no external file at given path: {self._abs_path}")
            else:
                return

        # prepare target_file path
        target_file_path = os.path.join(dir_path, os.path.basename(self._abs_path))

        # move or copy
        if mode == "copy":
            # copy
            shutil.copy2(self._abs_path, target_file_path)
        elif mode == "move":
            shutil.move(self._abs_path, target_file_path)

        # register new path
        self._abs_path = target_file_path
