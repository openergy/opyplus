"""Weather data design condition module."""


class DesignCondition:
    """
    Class describing E+ weather data design condition.

    Parameters
    ----------
    name: str
    values: list

    Attributes
    ----------
    name: str
    values: list
    """

    def __init__(self, name, values):
        # todo: [GL] checks
        self.name = name
        self.values = values
