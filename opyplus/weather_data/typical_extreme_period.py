"""Typical extreme period module."""


class TypicalExtremePeriod:
    """
    Typical extreme period class.

    Parameters
    ----------
    name
    period_type
    start_day
    end_day

    # TODO[GL] fill docstring

    Attributes
    ----------
    name
    period_type
    start_day
    end_day
    """

    def __init__(self, name, period_type, start_day, end_day):
        self.name = name
        self.period_type = period_type
        self.start_day = start_day
        self.end_day = end_day
