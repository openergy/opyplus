import os

from oplus.configuration import CONFIG

default_logger_name = __name__ if CONFIG.logger_name is None else CONFIG.logger_name


class EPWError(Exception):
    pass


class EPW:
    def __init__(self, path, logger_name=None, encoding=None):
        if not os.path.exists(path):
            raise EPWError("No file at given path: '%s'." % path)
        self._path = path
        self._logger_name = logger_name
        self._encoding = encoding

        self._content = open(self._path, "r",
                             encoding=CONFIG.encoding if self._encoding is None else self._encoding).read()

    def _parse(self, file_like):
        # todo: code

        pass

    def save_as(self, file_or_path):
        is_path = isinstance(file_or_path, str)
        f = (open(file_or_path, "w", encoding=CONFIG.encoding if self._encoding is None else self._encoding)
             if is_path else file_or_path)

        f.write(self._content)

        if is_path:
            f.close()