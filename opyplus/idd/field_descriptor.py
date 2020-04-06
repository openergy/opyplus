"""Idd field_descriptor module."""
import re
import unidecode

from ..exceptions import FieldValidationError
from ..epm.record import Record
from ..epm.link import Link, NONE_LINK
from ..epm.record_hook import RecordHook, NONE_RECORD_HOOK
from ..epm.external_file import ExternalFile
from .util import isinstance_str

MAX_FIELD_LENGTH = 100

spaces_and_newlines_pattern = re.compile(r"[\n\r\s]+")
not_python_var_pattern = re.compile(r"(^[^\w]+)|([^\w\d]+)")
multiple_underscores_pattern = re.compile(r"[_]{2,}")


def _var_name_to_ref(name):
    ref = re.sub(not_python_var_pattern, "_", name.lower())
    return re.sub(multiple_underscores_pattern, "_", ref)


class FieldDescriptor:
    """
    Idd field descriptor class.

    Parameters
    ----------
    table_descriptor: opyplus.idd.table_descriptor.TableDescriptor
    index: int
    field_basic_type: {"A", "N"}
    name: str or None

    Attributes
    ----------
    table_descriptor: opyplus.idd.table_descriptor.TableDescriptor
    index: int
    field_basic_type: {"A", "N"}
    name: str or None
    ref: str or None
    tags: dict

    Notes
    -----
    No checks implemented (idd is considered as ok).
    """

    BASIC_FIELDS = ("integer", "real", "alpha", "choice", "node", "external-list")

    def __init__(self, table_descriptor, index, field_basic_type, name=None):
        self.table_descriptor = table_descriptor
        if field_basic_type not in ("A", "N"):
            raise ValueError("Unknown field type: '%s'." % field_basic_type)
        self.index = index
        self.basic_type = field_basic_type  # A -> alphanumeric, N -> numeric
        self.name = name
        self.ref = None if name is None else _var_name_to_ref(name)
        self.tags = {}

        # used for error messages on extensible fields
        self._extensible_info = None
        self._detailed_type = None

    # construct
    def append_tag(self, ref, value=None):
        """
        Append a tag.

        Parameters
        ----------
        ref: str
        value
        """
        if ref not in self.tags:
            self.tags[ref] = []

        # manage value
        if value is None:
            return

        self.tags[ref].append(value)

    def set_extensible_info(self, cycle_start, cycle_len, cycle_pattern):
        """
        Set the extensible info.

        Parameters
        ----------
        cycle_start: int
        cycle_len: int
        cycle_pattern: int
        """
        self._extensible_info = (cycle_start, cycle_len, cycle_pattern)

    # deserialize
    def deserialize(self, value, index, check_length=True):
        """
        Deserialize.

        Parameters
        ----------
        value
        index: int
        check_length: bool
            default True

        Notes
        -----
        index is used for extensible fields error messages (if given)
        """
        # -- serialize if not raw type
        # transform to string if external file
        if isinstance(value, ExternalFile):
            value = value.naive_short_ref

        # transform to string if record
        if isinstance(value, Record):
            try:
                value = value[0]
            except IndexError:
                raise ValueError("can't set given record because it does not have a name field")

        # -- prepare if string
        if isinstance(value, str):
            # change multiple spaces to mono spaces
            value = re.sub(spaces_and_newlines_pattern, lambda x: " ", value.strip())

            # see if still not empty
            if value == "":
                return None

            # make ASCII compatible
            value = unidecode.unidecode(value)  # todo: is this still useful ?

            # make lower case if not retaincase
            if "retaincase" not in self.tags:
                value = value.lower()

            # check not too big
            if check_length and (len(value) >= MAX_FIELD_LENGTH):
                raise FieldValidationError(
                    f"Field has more than {MAX_FIELD_LENGTH} characters which is the limit. "
                    f"{self.get_error_location_message(value, index=index)}"
                )

        # transform to external file if relevant
        if self.is_file_name:
            value = ExternalFile.deserialize(value)

        # -- deserialize

        # numeric types
        if self.detailed_type in ("integer", "real"):
            # manage none
            if value is None:
                return None

            # special values: auto-calculate, auto-size, use-weather-file
            if value in ("autocalculate", "autosize", "useweatherfile"):
                return value

            if self.detailed_type == "integer":
                try:
                    try:
                        return int(value)
                    except ValueError:
                        i = float(value)
                        if not i.is_integer():
                            raise ValueError
                        return int(i)
                except Exception:
                    raise FieldValidationError(
                        f"Couldn't parse to integer. {self.get_error_location_message(value, index=index)}"
                    )

            try:
                return float(value)
            except Exception:
                raise FieldValidationError(
                    f"Couldn't parse to float. {self.get_error_location_message(value, index=index)}"
                )

        # simple string types
        if self.detailed_type in ("alpha", "choice", "node", "external-list"):
            # manage none
            if value is None:
                return None

            # ensure it was str
            if not isinstance_str(value):
                raise FieldValidationError(
                    f"Value must be a string. {self.get_error_location_message(value, index=index)}"
                )
            return value

        # manage hooks (eplus reference)
        if self.detailed_type == "reference":
            # manage None
            if value is None:
                return NONE_RECORD_HOOK

            # reference class name appears in v9.0.1
            references = self.tags.get("reference", [])
            # table_name, index, value, references, class_references
            return RecordHook(references, index, value)

        # manage links (eplus object-list)
        if self.detailed_type == "object-list":
            # manage None
            if value is None:
                return NONE_LINK

            return Link(self.tags["object-list"], value, index)

        raise RuntimeError("should not be here")

    # get info
    @property
    def is_required(self):
        """
        Return whether field is required.

        Returns
        -------
        bool
        """
        return "required-field" in self.tags

    @property
    def is_file_name(self):
        """
        Return whether field is a file name.

        Returns
        -------
        bool
        """
        # we don't add this to detailed_type because can be a file name and something else (for example object-list)
        return "file_name" in self.ref

    def check_not_required(self):
        """
        Check that the field is not required.

        Raises
        ------
        FieldValidationError
            if field is required
        """
        if self.is_required:
            raise FieldValidationError(f"Field is required. {self.get_error_location_message()}")

    @property
    def detailed_type(self):
        """
        Get the detailed type.

        Returns
        -------
        "integer", "real", "alpha", "choice", "reference", "object-list", "external-list", "node"

        Notes
        -----
        Uses EPlus double approach of type ('type' tag, and/or 'key', 'object-list', 'external-list', 'reference' tags)
        to determine detailed type.
        """
        if self._detailed_type is None:
            if ("reference" in self.tags) or ("reference-class-name" in self.tags):
                self._detailed_type = "reference"
            elif "type" in self.tags:
                self._detailed_type = self.tags["type"][0].lower()  # idd is not very rigorous on case
            elif "key" in self.tags:
                self._detailed_type = "choice"
            elif "object-list" in self.tags:
                self._detailed_type = "object-list"
            elif "external-list" in self.tags:
                self._detailed_type = "external-list"
            elif self.basic_type == "A":
                self._detailed_type = "alpha"
            elif self.basic_type == "N":
                self._detailed_type = "real"
            else:
                raise ValueError("Can't find detailed type.")
        return self._detailed_type

    def get_error_location_message(self, value=None, index=None):
        """
        Get the error location message.

        Parameters
        ----------
        value
        index: int or None

        Returns
        -------
        str
        """
        # manage extensible field ref if relevant
        if (index is not None) and (self._extensible_info is not None) and (index >= self._extensible_info[0]):
            cycle_num = (index - self._extensible_info[0]) // self._extensible_info[1] + 1
            ref = self._extensible_info[2].replace(r"(\d+)", str(cycle_num))
        else:
            ref = self.ref

        return f"Table: {self.table_descriptor.table_name}, index: {self.index}, ref: {ref}" +\
               ("." if value is None else f", value: {value}.")
