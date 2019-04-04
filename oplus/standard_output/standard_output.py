import logging
import collections

from ..util import to_buffer
from .parse_eso import parse_eso, FREQUENCIES
from .switch_instants import switch_to_datetime_instants

logger = logging.getLogger(__name__)


class StandardOutput:
    def __init__(self, buffer_or_path):
        """
        Parameters
        ----------
        buffer_or_path

        Initially, standard_output will have tuple instants (using 'year', 'month', 'day', 'hour', 'minute' columns,
            depending on given frequency). It is possible to change to datetime mode later.
        """
        self._path = None
        self._path, buffer = to_buffer(buffer_or_path)
        with buffer as f:
            self._raw_environments, self._raw_variables_info, self._dfs = parse_eso(f)
        self._start_year = None

    @property
    def has_tuple_instants(self):
        return self._start_year is None

    def switch_to_datetime_instants(self, start_year):
        # leave if not relevant
        if self._start_year == start_year:
            return

        # check not a year switch
        if (self._start_year is not None) and (self._start_year != start_year):
            raise ValueError("Can't change start_year when already datetime instants, switch to tuple instants first.")

        # switch all dataframes
        new_dfs = {}
        for env_title, env_data in self._dfs.items():
            env_dfs = {}
            new_dfs[env_title] = env_dfs
            for eplus_frequency, df in env_data.items():
                env_dfs[eplus_frequency] = None if df is None else switch_to_datetime_instants(
                    df, start_year, eplus_frequency)

        # store result and start year
        self._dfs = new_dfs
        self._start_year = start_year

    def get_data(self, environment_title_or_num=-1, frequency=None):
        """
        Parameters
        ----------
        environment_title_or_num
        frequency: 'str', default None
            'timestep', 'hourly', 'daily', 'monthly', 'annual', 'run_period'
            If None, will look for the smallest frequency of environment.
        """

        # manage environment num
        if isinstance(environment_title_or_num, int):
            environment_title = tuple(self._raw_environments.keys())[environment_title_or_num]
        else:
            environment_title = environment_title_or_num

        if environment_title not in self._dfs:
            raise ValueError(f"No environment named {environment_title}. Available environments: {tuple(self._dfs)}.")

        # get environment dataframes
        environment_dfs = self._dfs[environment_title]

        # find first non null frequency if not given
        if frequency is None:
            for frequency in FREQUENCIES:
                if environment_dfs[frequency] is not None:
                    break

        # check frequency
        if frequency not in FREQUENCIES:
            raise ValueError(f"Unknown frequency: {frequency}. Available frequencies: {FREQUENCIES}")

        return self._dfs[environment_title][frequency]

    def get_environments(self):
        environments = collections.OrderedDict()
        for e in self._raw_environments.values():
            # base info
            env = collections.OrderedDict((
                ("latitude", e.latitude),
                ("longitude", e.longitude),
                ("timezone_offset", e.timezone_offset),
                ("elevation", e.elevation)
            ))

            # add count info
            for freq in FREQUENCIES:
                df = self.get_data(environment_title_or_num=e.title, frequency=freq)
                env[f"nb_values_{freq}"] = 0 if df is None else len(df)

            # store
            environments[e.title] = env

        return environments

    def get_variables(self):
        _variables = []
        for v in self._raw_variables_info.values():
            # base info
            var = collections.OrderedDict((
                ("code", v.code),
                ("key_value", v.key_value),
                ("name", v.name),
                ("ref", f"{v.key_value},{v.name}"),
                ("unit", v.unit),
                ("frequency", v.frequency),
                ("info", v.info)
            ))

            # add environments info
            var["environments"] = [
                env_title for env_title in self._raw_environments if self._dfs[env_title] is not None]

            # store
            _variables.append(var)

        # sort, create dict and return
        return collections.OrderedDict(
            (f"{var['frequency']},{var['ref']}", var) for var in
            sorted(_variables, key=lambda x: (x["frequency"], x["ref"]))
        )

    def get_info(self):
        msg = "Standard output\n"
        msg += f"\tinstants: {'tuple' if self.has_tuple_instants else 'datetime'}\n"
        msg += "\tenvironments:\n"
        for env_title, env_info in self.get_environments().items():
            msg += f"\t\t'{env_title}'\n"
            for k, v in env_info.items():
                msg += f"\t\t\t{k}: {v}\n"
        msg += "\tvariables:\n"
        msg += "\t\t" + "\n\t\t".join(self.get_variables())

        return msg
