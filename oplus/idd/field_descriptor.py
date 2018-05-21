import re
import unidecode

spaces_pattern = re.compile("\s+")


def to_num(raw_value):
    if isinstance(raw_value, str):
        if raw_value in ("autocalculate", "autosize"):  # raw_values are always lowercase
            return raw_value
        try:
            return int(raw_value)
        except ValueError:
            return float(raw_value)


class FieldDescriptor:
    """
    No checks implemented (idf is considered as ok).
    """
    BASIC_FIELDS = ("integer", "real", "alpha", "choice", "node", "external-list")

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

    def cleanup_and_check_raw_value(self, unsafe_raw_value):
        # manage None
        if unsafe_raw_value is None:
            unsafe_raw_value = ""

        # check is string
        assert isinstance(unsafe_raw_value, str), f"'raw_value' must be a string, got {type(unsafe_raw_value)}"

        # change multiple spaces to mono spaces
        raw_value = re.sub(spaces_pattern, lambda x: " ", unsafe_raw_value.strip())

        # make ASCII compatible
        raw_value = unidecode.unidecode(raw_value)

        # make lower case if not retaincase
        if not self.has_tag("retaincase"):
            raw_value = raw_value.lower()

        # check not too big
        assert len(raw_value) <= 100, "Field has more than 100 characters which is the limit."

        # check if num and not None
        if (raw_value != "") and (self.basic_type == "N"):
            to_num(raw_value)

        return raw_value

    def basic_parse(self, raw_value):
        """
        Parses raw value (string or None) to string, int, float or None.
        """
        # no value
        if (raw_value is None) or (raw_value == ""):
            return None

        # alphabetical
        if self.basic_type == "A":
            return raw_value

        # numeric
        if isinstance(raw_value, str):
            return to_num(raw_value)

        # in case has already been parsed
        elif type(raw_value) in (int, float):
            return raw_value

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
                self._detailed_type = self._tags_d["type"][0].lower()  # idd is not very rigorous on case
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

