"""weather_data ground temperature module."""


class GroundTemperature:
    """
    Class describing an E+ weather Ground Temperature object.

    Parameters
    ----------
    depth: float
    soil_conductivity: float
    soil_density: float
    soil_specific_heat: float
    monthly_average_ground_temperatures: list of float

    Attributes
    ----------
    depth: float
    soil_conductivity: float
    soil_density: float
    soil_specific_heat: float
    monthly_average_ground_temperatures: list of float
    """

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
