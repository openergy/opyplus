import os
import logging

from oplus import CONF
from .file_content import FileContent

logger = logging.getLogger(__name__)


def get_external_files_dir_name(model_name=None):
    if model_name is None:
        model_name = CONF.default_model_name
    return model_name + CONF.external_files_suffix


class ExternalFile:
    @classmethod
    def deserialize(cls, value):
        if value is None:
            return NONE_EXTERNAL_FILE

        if isinstance(value, FileContent):
            return cls(value.name, content=value.content)

        return cls(value)

    def __init__(self, ref, content=None):
        # manage NONE_EXTERNAL_FILE
        if ref is None:
            return

        self._ref = ref
        _, self._naive_short_ref = os.path.split(ref)
        self._external_file_manager = None
        self._content = content

    def _dev_activate(self, external_files_manager):
        # return if already active
        if self._external_file_manager is not None:
            return

        # store external file manager and register
        self._external_file_manager = external_files_manager
        external_files_manager.register(self)

    def _dev_prepare_content(self):
        if self._content is not None:
            return self._content

        # manage content (depending on existence of initial path)
        if not os.path.isfile(self._ref):
            logger.warning(
                f"no file found at given path, content will be considered as empty ({self._ref})")
            content = None
        else:
            with open(self._ref, encoding=CONF.encoding) as f:
                content = f.read()

        return content

    def _dev_unregister(self):
        self._external_file_manager.unregister(self)

    def __repr__(self):
        return f"<ExternalFile: {self._ref}>"

    @property
    def ref(self):
        return self._ref

    @property
    def naive_short_ref(self):
        return self._naive_short_ref

    @property
    def short_ref(self):
        return self._external_file_manager.short_refs[self.ref]

    def get_content(self):
        return self._external_file_manager.get_content(self._ref)

    # def activate(self, model_file_path=None):
    #     # if initial path is absolute, no need for model file path
    #     if os.path.isabs(self._initial_path):
    #         self._abs_path = os.path.normpath(self._initial_path)
    #         return
    #
    #     # manage model file path
    #     model_file_path = to_abs_model_file_path(model_file_path)
    #     self._abs_path = os.path.normpath(os.path.join(model_file_path, self._initial_path))
    #
    # def get_path(self, mode=None, model_file_path=None):
    #     """
    #     Parameters
    #     ----------
    #     mode: str, default 'relative'
    #         'relative', 'absolute'
    #     model_file_path
    #     """
    #     if mode in ("relative", None):
    #         # manage model file path
    #         model_file_path = to_abs_model_file_path(model_file_path)
    #
    #         # return rel path
    #         return os.path.relpath(self._abs_path, os.path.dirname(model_file_path))
    #
    #     elif mode == "absolute":
    #         return self._abs_path
    #
    #     raise ValueError(f"unknown mode: '{mode}'")
    #
    # def check_file_exists(self):
    #     if not os.path.exists(self._abs_path):
    #         raise FileNotFoundError(f"external file not found at given path: {self._abs_path}")
    #
    # def transfer(self, dir_path, mode="copy", raise_if_not_found=True):
    #     """
    #     Parameters
    #     ----------
    #     dir_path: target dir path
    #     mode: str, default "copy"
    #         "copy", "move", "hold_back"
    #     raise_if_not_found
    #     """
    #     # manage if file does not exist
    #     exists = os.path.isfile(self._abs_path)
    #     if not exists:
    #         if raise_if_not_found:
    #             raise FileNotFoundError(f"no external file at given path: {self._abs_path}")
    #         else:
    #             return
    #
    #     # prepare absolute target_file path
    #     if not os.path.isabs(dir_path):
    #         dir_path = os.path.join(os.getcwd(), dir_path)
    #     target_file_path = os.path.normpath(os.path.join(dir_path, os.path.basename(self._abs_path)))
    #
    #     # move or copy
    #     if mode == "copy":
    #         # copy
    #         shutil.copy2(self._abs_path, target_file_path)
    #     elif mode == "move":
    #         shutil.move(self._abs_path, target_file_path)
    #     elif mode == "hold_back":
    #         pass
    #     else:
    #         raise ValueError("unknown mode")
    #
    #     # register new path
    #     self._abs_path = target_file_path

NONE_EXTERNAL_FILE = ExternalFile(None)
