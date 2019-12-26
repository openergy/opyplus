from .data_containers import DataContainer

# frequencies
EACH_CALL = "each_call"
TIMESTEP = "timestep"
HOURLY = "hourly"
DAILY = "daily"
MONTHLY = "monthly"
ANNUAL = "annual"
RUN_PERIOD = "run_period"

FREQUENCIES = EACH_CALL, TIMESTEP, HOURLY, DAILY, MONTHLY, ANNUAL, RUN_PERIOD

SUB_HOURLY = "sub_hourly"

container_characteristics = {
    EACH_CALL: dict(
        pandas_freq=None,
        instant_columns=(
            "month",
            "day",
            "hour",
            "minute",
            "end_minute",
            "dst",
            "day_type"
        )),
    TIMESTEP: dict(
        pandas_freq="?",
        instant_columns=(
            "month",
            "day",
            "hour",
            "minute",
            "end_minute",
            "dst",
            "day_type"
        )),
    HOURLY: dict(
        pandas_freq="H",
        instant_columns=(
            "month",
            "day",
            "hour",
            "minute",
            "end_minute",
            "dst",
            "day_type"
        )),
    DAILY: dict(
        pandas_freq="D",
        instant_columns=(
            "month",
            "day",
            "dst",
            "day_type"
        )),
    MONTHLY: dict(
        pandas_freq="MS",
        instant_columns=("month",)),
    ANNUAL: dict(
        pandas_freq="YS",
        instant_columns=("year",)),
    RUN_PERIOD: dict(
        pandas_freq=None,
        instant_columns=()
    )
}


class OutputEnvironment:
    def __init__(self, title, latitude, longitude, timezone_offset, elevation, variables_by_freq):
        self.title = title
        self.latitude = latitude
        self.longitude = longitude
        self.timezone_offset = timezone_offset
        self.elevation = elevation

        # prepare data containers and variables by code
        self._data_containers_by_freq = dict()
        self._variables_code_to_freq = dict()

        for (freq, variables) in variables_by_freq.items():
            characteristics = container_characteristics[freq]
            self._data_containers_by_freq[freq] = DataContainer(
                variables,
                freq,
                characteristics["instant_columns"],
                pandas_freq=characteristics["pandas_freq"]
            )
            for var in variables:
                self._variables_code_to_freq[var.code] = freq

    def _dev_register_instant(self, simplified_frequency, *args):
        if simplified_frequency == SUB_HOURLY:
            # each call
            for freq in (EACH_CALL, TIMESTEP, HOURLY):
                try:
                    self._data_containers_by_freq[freq].register_instant(*args)
                except KeyError:
                    pass
            return
        self._data_containers_by_freq[simplified_frequency].register_instant(*args)

    def _dev_register_value(self, code, value):
        self._data_containers_by_freq[self._variables_code_to_freq[code]].register_value(code, value)

    def _dev_create_datetime_index(self, start_year):
        for container in self._data_containers_by_freq.values():
            container.create_datetime_index(start_year)

    def _dev_build_dfs(self):
        for freq, container in self._data_containers_by_freq.items():
            container.build_df()

    def _dev_get_data_conainers_by_freq(self):
        return self._data_containers_by_freq.copy()

    # --------------------------------------------- public api ---------------------------------------------------------
    def get_data(self, frequency=None):
        """
        Parameters
        ----------
        frequency: str, default None
            each_call, timestep, hourly, daily, monthly, annual, run_period
            if None, will take the first found in the list above

        Returns
        -------
        dataframe
        """
        # find first non null frequency if not given
        if frequency is None:
            for frequency in FREQUENCIES:
                if frequency in self._data_containers_by_freq:
                    break

        # check frequency
        if frequency not in FREQUENCIES:
            raise ValueError(f"Unknown frequency: {frequency}. Available frequencies: {self._data_containers_by_freq}")

        # leave if no data
        if frequency not in self._data_containers_by_freq:
            return None

        return self._data_containers_by_freq[frequency].df

    def get_info(self, env_num=None):
        num_info = "" if env_num is None else f" ({env_num})"
        msg = f"{self.title}{num_info}\n"
        for var in ("latitude", "longitude", "timezone_offset", "elevation"):
            msg += f"  {var}: {getattr(self, var)}\n"
        return msg
