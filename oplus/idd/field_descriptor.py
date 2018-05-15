class FieldDescriptor:
    """
    No checks implemented (idf is considered as ok).
    """
    def __init__(self, field_basic_type, name=None):
        if field_basic_type not in ("A", "N"):
            raise ValueError("Unknown field type: '%s'." % field_basic_type)
        self.basic_type = field_basic_type  # A -> alphanumeric, N -> numeric
        self.name = name
        self._tags_d = {}

        self._detailed_type = None

    @property
    def tags(self):
        return sorted(self._tags_d)

    def add_tag(self, ref, value=None):
        if ref not in self._tags_d:
            self._tags_d[ref] = []
        if value is not None:
            self._tags_d[ref].append(value)

    def get_tag(self, ref):
        """
        Returns tag belonging to field descriptor. If 'note', will be string, else list of elements.
        """
        if ref == "note":  # memo is for object descriptors
            return " ".join(self._tags_d[ref])
        return self._tags_d[ref]

    def has_tag(self, ref):
        return ref in self._tags_d

    def basic_parse(self, value):
        """
        Parses raw value (string or None) to string, int, float or None.
        """
        # no value
        if (value is None) or (value == ""):
            return None

        # alphabetical
        if self.basic_type == "A":
            return str(value)

        # numeric
        if type(value) is str:
            if value.lower() in ("autocalculate", "autosize"):
                return value
            try:
                return int(value)
            except ValueError:
                return float(value)

        # in case has already been parsed
        elif type(value) in (int, float):
            return value

    @property
    def detailed_type(self):
        """
        Uses EPlus double approach of type ('type' tag, and/or 'key', 'object-list', 'external-list', 'reference' tags)
        to determine detailed type.
        Returns
        -------
        "integer", "real", "alpha", "choice", "reference", "object-list", "external_list", "node"
        """
        if self._detailed_type is None:
            if "reference" in self._tags_d:
                self._detailed_type = "reference"
            elif "type" in self._tags_d:
                self._detailed_type = self._tags_d["type"][0].lower()
            elif "key" in self._tags_d:
                self._detailed_type = "choice"
            elif "object-list" in self._tags_d:
                self._detailed_type = "object-list"
            elif "external-list" in self._tags_d:
                self._detailed_type = "external-list"
            elif self.basic_type == "A":
                self._detailed_type = "alpha"
            elif self.basic_type == "N":
                self._detailed_type = "real"
            else:
                raise ValueError("Can't find detailed type.")
        return self._detailed_type

    @staticmethod
    def name_to_formatted_name(name):
        """
        Returns formatted name of variable (lower case).
        """
        return name.lower()
