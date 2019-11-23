import logging
import os
import textwrap

from slugify import slugify

from ..util import to_buffer
from .parse_eso import parse_eso

logger = logging.getLogger(__name__)


class StandardOutput:
    def __init__(self, buffer_or_path, start_year=None, print_function=lambda x: None):
        """
        Parameters
        ----------
        buffer_or_path

        Initially, standard_output will have tuple instants (using 'year', 'month', 'day', 'hour', 'minute' columns),
            depending on given frequency). It is possible to create a datetime index afterwards.

        StandardOutput datetime index respects left convention: instant 00:00 covers following range: [00:00, 01:00[.
        !! this is not the same convention as in weather data chapter !!
        """
        self._path = None
        self._path, buffer = to_buffer(buffer_or_path)
        self._start_year = None
        with buffer as f:
            self._environments_by_title, self._variables_by_freq = parse_eso(f, print_function=print_function)
        if start_year is not None:
            self.create_datetime_index(start_year)

    # --------------------------------------------- public api ---------------------------------------------------------
    def create_datetime_index(self, start_year):
        for env in self._environments_by_title.values():
            env._dev_create_datetime_index(start_year)
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
            if len(self._environments_by_title) < (environment_title_or_num + 1):
                raise ValueError(
                    f"Environment number {environment_title_or_num} does not exist. "
                    f"Last environment: {len(self._environments_by_title - 1)}"
                )
            environment_title = tuple(self._environments_by_title)[environment_title_or_num]
        else:
            environment_title = environment_title_or_num

        if environment_title not in self._environments_by_title:
            raise ValueError(
                f"No environment named {environment_title}. "
                f"Available environments: {tuple(self._environments_by_title)}."
            )

        return self._environments_by_title[environment_title].get_data(frequency=frequency)

    def get_environments(self):
        return self._environments_by_title.copy()

    def get_variables(self):
        return self._variables_by_freq.copy()

    def get_info(self):
        msg = "Standard output\n"

        # environments
        msg += "  environments\n"
        for i, env in enumerate(self._environments_by_title.values()):
            msg += textwrap.indent(env.get_info(env_num=i), "    ")

        # variables
        msg += "  variables\n"
        for freq, variables in self._variables_by_freq.items():
            msg += f"    {freq}\n"
            for var in variables:
                msg += f"      {var.ref} ({var.code})\n"

        return msg

    def to_csv(self, dir_path, sep=";", decimal=","):
        # create dir path if needed
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)

        # dump data
        for i, env in enumerate(self._environments_by_title.values()):
            slug_env_title = slugify(env.title)
            for freq, container in env._dev_get_data_conainers_by_freq().items():
                file_path = os.path.join(dir_path, f"{i}#{slug_env_title}#{freq}.csv")
                container.df.to_csv(file_path, sep=sep, decimal=decimal)
