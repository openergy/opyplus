"""Simulation information module."""
import json
import collections


class Info:
    """
    Class containing a number of information about an E+ simulation.

    This information is stored by opyplus on a json file on the simulation directory.

    Parameters
    ----------
    status: {'empty', 'running', 'finished', 'failed'}
    eplus_version: tuple of int
    """

    def __init__(self, status, eplus_version):
        self._dev_status = status  # empty, running, finished, failed (a simulation necessarily has input files)
        self._dev_eplus_version = eplus_version

    @classmethod
    def from_json(cls, path):
        """
        Load from json file.

        Parameters
        ----------
        path: str

        Returns
        -------
        Info
        """
        with open(path) as f:
            json_data = json.load(f)
        eplus_version = tuple(json_data["eplus_version"])
        status = json_data["status"]
        return cls(status, eplus_version)

    @property
    def status(self):
        """
        Get simulation status.

        Returns
        -------
        str
        """
        return self._dev_status

    @property
    def eplus_version(self):
        """
        Get E+ version.

        Returns
        -------
        int
            Major
        int
            minor
        int
            patch
        """
        return self._dev_eplus_version

    def to_json_data(self):
        """
        Get Info as a json-serializable dict.

        Returns
        -------
        dict
        """
        return collections.OrderedDict((
            ("status", self.status),
            ("eplus_version", self.eplus_version)
        ))

    def to_json(self, path):
        """
        Write Info as json to a file.

        Parameters
        ----------
        path: str
            file path
        """
        with open(path, "w") as f:
            json.dump(self.to_json_data(), f, indent=4)
