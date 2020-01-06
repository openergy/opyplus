"""Weather data design condition module."""


class DesignCondition:
    """
    Class describing E+ weather data design condition.

    Parameters
    ----------
    name: str
    values
    # TODO [GL] fill in docstring

    Attributes
    ----------
    name: str
    values
    """

    def __init__(self, name, values):
        # todo: [GL] checks
        self.name = name
        self.values = values
