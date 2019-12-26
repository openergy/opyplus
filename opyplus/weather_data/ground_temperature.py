class GroundTemperature:
    def __init__(
            self,
            depth,
            soil_conductivity,
            soil_density,
            soil_specific_heat,
            monthly_average_ground_temperatures  # 12 values
    ):
        # todo: [GL] checks
        self.depth = depth
        self.soil_conductivity = soil_conductivity
        self.soil_density = soil_density
        self.soil_specific_heat = soil_specific_heat
        self.monthly_average_ground_temperatures = monthly_average_ground_temperatures
