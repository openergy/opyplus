from .parse_eso import EACH_CALL, TIMESTEP, HOURLY, DAILY, MONTHLY, ANNUAL, RUN_PERIOD, SUB_HOURLY
from .data_containers import SubHourlyDataContainer, DailyDataContainer, MonthlyDataContainer, AnnualDataContainer, \
    RunPeriodDataContainer


class OutputEnvironment:
    def __init__(self, title, latitude, longitude, timezone_offset, elevation, variables_by_freq):
        self.title = title
        self.latitude = latitude
        self.longitude = longitude
        self.timezone_offset = timezone_offset
        self.elevation = elevation

        # prepare data containers and variables by code
        self.data_containers_by_freq = dict()
        self.variables_code_to_freq = dict()

        for (freq, variables) in variables_by_freq.items():
            self.data_containers_by_freq[freq] = {
                EACH_CALL: SubHourlyDataContainer,
                TIMESTEP: SubHourlyDataContainer,
                HOURLY: SubHourlyDataContainer,
                DAILY: DailyDataContainer,
                MONTHLY: MonthlyDataContainer,
                ANNUAL: AnnualDataContainer,
                RUN_PERIOD: RunPeriodDataContainer
            }[freq](variables)
            for var in variables:
                self.variables_code_to_freq[var.code] = freq

    def register_instant(self, simplified_frequency, *args):
        if simplified_frequency == SUB_HOURLY:
            # each call
            for freq in (EACH_CALL, TIMESTEP, HOURLY):
                try:
                    self.data_containers_by_freq[freq].register_instant(*args)
                except KeyError:
                    pass
            return
        self.data_containers_by_freq[simplified_frequency].register_instant(*args)

    def register_value(self, code, value):
        self.data_containers_by_freq[self.variables_code_to_freq[code]].register_value(code, value)

    def create_datetime_index(self, start_year):
        for container in self.data_containers_by_freq.values():
            container.create_datetime_index(start_year)
