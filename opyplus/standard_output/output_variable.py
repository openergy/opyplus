"""Output variable module."""


class OutputVariable:
    """
    Output variable class (represents an EnergyPlus output variable).

    Parameters
    ----------
    code
    key_value
    name
    unit
    frequency
    info

    Attributes
    ----------
    code
    key_value
    name
    unit
    frequency
    info
    """

    def __init__(self, code, key_value, name, unit, frequency, info):
        self.code = code
        self.key_value = key_value
        self.name = name
        self.unit = unit
        self.frequency = frequency
        self.info = info

    @property
    def ref(self):
        """
        Get ref.

        Returns
        -------
        str
        """
        return f"{self.key_value},{self.name}"

    def __repr__(self):
        """
        Get repr including ref and code.

        Returns
        -------
        str
        """
        return f"{self.ref} ({self.code})"

    def __str__(self):
        """
        Cast to string, includes ref, code, frequency, unit, info.

        Returns
        -------
        str
        """
        msg = f"Variable {self.ref} ({self.code}\n"
        msg += f"  frequency: {self.frequency}\n"
        msg += f"  unit: {self.unit}\n"
        if self.info != "":
            msg += f"  info: {self.info}\n"
        return msg.strip()
