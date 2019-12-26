import os
import logging

from opyplus import CONF
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


NONE_EXTERNAL_FILE = ExternalFile(None)
