class OutputVariable:
    def __init__(self, code, key_value, name, unit, frequency, info):
        self.code = code
        self.key_value = key_value
        self.name = name
        self.unit = unit
        self.frequency = frequency
        self.info = info

    @property
    def ref(self):
        return f"{self.key_value},{self.name}"

    def __repr__(self):
        return f"{self.ref} ({self.code})"

    def __str__(self):
        msg = f"Variable {self.ref} ({self.code}\n"
        msg += f"  frequency: {self.frequency}\n"
        msg += f"  unit: {self.unit}\n"
        if self.info != "":
            msg += f"  info: {self.info}\n"
