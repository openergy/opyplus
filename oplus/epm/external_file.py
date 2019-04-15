import os
import shutil


def to_abs_model_file_path(model_file_path):
    if model_file_path is None:
        return os.path.abspath(os.curdir)
    if not os.path.isabs(model_file_path):
        return os.path.join(os.path.abspath(os.curdir), model_file_path)
    return model_file_path


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

    def activate(self, model_file_path=None):
        # if initial path is absolute, no need for model file path
        if os.path.isabs(self._initial_path):
            self._abs_path = os.path.normpath(self._initial_path)
            return

        # manage model file path
        model_file_path = to_abs_model_file_path(model_file_path)
        self._abs_path = os.path.normpath(os.path.join(os.path.dirname(model_file_path), self._initial_path))

    def get_path(self, mode=None, model_file_path=None):
        """
        Parameters
        ----------
        mode: str, default 'relative'
            'relative', 'absolute'
        model_file_path
        """
        if mode in ("relative", None):
            # manage model file path
            model_file_path = to_abs_model_file_path(model_file_path)

            # return rel path
            return os.path.relpath(self._abs_path, os.path.dirname(model_file_path))

        elif mode == "absolute":
            return self._abs_path

        raise ValueError(f"unknown mode: '{mode}'")

    def check_file_exists(self):
        if not os.path.exists(self._abs_path):
            raise FileNotFoundError(f"external file not found at given path: {self._abs_path}")

    def transfer(self, dir_path, mode="copy", raise_if_not_found=True):
        """
        Parameters
        ----------
        dir_path: target dir path
        mode: str, default "copy"
            "copy", "move", "hold_back"
        raise_if_not_found
        """
        # manage if file does not exist
        exists = os.path.isfile(self._abs_path)
        if not exists:
            if raise_if_not_found:
                raise FileNotFoundError(f"no external file at given path: {self._abs_path}")
            else:
                return

        # prepare absolute target_file path
        if not os.path.isabs(dir_path):
            dir_path = os.path.join(os.getcwd(), dir_path)
        target_file_path = os.path.normpath(os.path.join(dir_path, os.path.basename(self._abs_path)))

        # move or copy
        if mode == "copy":
            # copy
            shutil.copy2(self._abs_path, target_file_path)
        elif mode == "move":
            shutil.move(self._abs_path, target_file_path)
        elif mode == "hold_back":
            pass
        else:
            raise ValueError("unknown mode")

        # register new path
        self._abs_path = target_file_path
