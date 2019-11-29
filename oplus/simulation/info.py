import json
import collections


class Info:
    def __init__(self, status, eplus_version):
        """
        Parameters
        ----------
        status: str
            empty: only input files
            running
            finished
            failed
        eplus_version: tuple
        """
        self._dev_status = status  # empty, running, finished, failed (a simulation necessarily has input files)
        self._dev_eplus_version = eplus_version

    @classmethod
    def from_json(cls, path):
        with open(path) as f:
            json_data = json.load(f)
        eplus_version = tuple(json_data["eplus_version"])
        status = json_data["status"]
        return cls(status, eplus_version)

    @property
    def status(self):
        return self._dev_status

    @property
    def eplus_version(self):
        return self._dev_eplus_version

    def to_json_data(self):
        return collections.OrderedDict((
            ("status", self.status),
            ("eplus_version", self.eplus_version)
        ))

    def to_json(self, path):
        with open(path, "w") as f:
            json.dump(self.to_json_data(), f, indent=4)
