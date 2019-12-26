import logging
import re

from .field_descriptor import FieldDescriptor
from .util import table_name_to_ref

logger = logging.getLogger(__name__)


class TableDescriptor:
    """
    Describes a EPlus record (see idd).
    """
    def __init__(self, table_name, group_name=None):
        self.table_name = table_name
        self.table_ref = table_name_to_ref(table_name)
        self.group_name = group_name
        # we use list (and not dict) because some field descriptors do not have a name (including non extensible tables)
        self._field_descriptors = []
        self._tags = {}

        # extensible management
        # (cycle_start, cycle_len, patterns) where patterns is (var_a_(\d+)_ref, var_b_(\d+)_ref, ...)
        self.extensible_info = None

    @property
    def field_descriptors(self):
        return self._field_descriptors

    @property
    def tags(self):
        return self._tags

    def add_tag(self, tag_ref, value=None):
        if tag_ref not in self._tags:
            self._tags[tag_ref] = []
        if value is not None:
            self._tags[tag_ref].append(value)

    def add_field_descriptor(self, fieldd_type, name=None):
        # create
        field_descriptor = FieldDescriptor(self, len(self._field_descriptors), fieldd_type, name=name)

        # append
        self._field_descriptors.append(field_descriptor)

        return field_descriptor

    def prepare_extensible(self):
        """
        This function finishes initialization, must be called once all field descriptors and tag have been filled.
        """
        # see if extensible and store cycle len
        for k in self._tags:
            if "extensible" in k:
                cycle_len = int(k.split(":")[1])
                break
        else:
            # not extensible
            return

        # find cycle start and prepare patterns
        cycle_start = None
        cycle_patterns = []
        for i, field_descriptor in enumerate(self._field_descriptors):
            # quit if finished
            if (cycle_start is not None) and (i >= (cycle_start + cycle_len)):
                break

            # set cycle start if not set yet
            if (cycle_start is None) and ("begin-extensible" in field_descriptor.tags):
                cycle_start = i

            # leave if cycle start not reached yet
            if cycle_start is None:
                continue

            # store pattern
            cycle_patterns.append(field_descriptor.ref.replace("1", r"(\d+)"))
        else:
            raise RuntimeError("cycle start not found")

        # detach unnecessary field descriptors
        self._field_descriptors = self._field_descriptors[:cycle_start + cycle_len]

        # store cycle info
        self.extensible_info = (cycle_start, cycle_len, tuple(cycle_patterns))

        # set field descriptor cycle_start index (for error messages while serialization)
        for i, fd in enumerate(self._field_descriptors[cycle_start:]):
            fd.set_extensible_info(cycle_start, cycle_len, cycle_patterns[i])

    @property
    def base_fields_nb(self):
        """
        base fields: without extensible
        """
        return len(self._field_descriptors) if self.extensible_info is None else self.extensible_info[0]

    def get_field_index(self, ref):
        # general case
        for pattern_num in range(self.base_fields_nb):
            field_descriptor = self._field_descriptors[pattern_num]
            if field_descriptor.ref is None:  # can happen
                continue
            if field_descriptor.ref == ref:
                return pattern_num

        # extensible
        ext_info = self.extensible_info
        if ext_info is not None:
            cycle_start, cycle_len, patterns = ext_info
            for pattern_num, pat in enumerate(patterns):
                match = re.fullmatch(pat, ref)
                if match is None:  # not found
                    continue
                # we found cycle
                cycle_num = int(match.group(1))

                # calculate and return index
                return cycle_start + (cycle_num-1)*cycle_len + pattern_num

        err_msg = f"No field of '{self.table_name}' has ref '{ref}'.\nAvailable fields: \n - "
        err_msg += "\n - ".join(fd.ref for fd in self._field_descriptors if fd.ref is not None)
        raise AttributeError(err_msg)

    def get_field_reduced_index(self, index):
        """
        reduced index: modulo of extensible has been applied
        """
        # return index if not extensible
        if self.extensible_info is None:
            return index

        # manage extensible
        cycle_start, cycle_len, _ = self.extensible_info

        # base field
        if index < cycle_start:
            return index

        # extensible field
        return cycle_start + ((index - cycle_start) % cycle_len)

    def get_field_descriptor(self, index):
        return self._field_descriptors[self.get_field_reduced_index(index)]

    def get_extended_name(self, index):
        """
        manages extensible names
        """
        field_descriptor = self.get_field_descriptor(index)
        if self.extensible_info is None:
            return field_descriptor.name
        cycle_start, cycle_len, _ = self.extensible_info
        cycle_num = (index - cycle_start) // cycle_len
        return None if field_descriptor.name is None else field_descriptor.name.replace("1", str(cycle_num))

    def get_info(self):
        header = f"{self.table_name} ({self.table_ref})"

        msg = f"{header}\n"
        for i, field_descriptor in enumerate(self.field_descriptors):
            msg += f" {i}" + (
                "\n" if field_descriptor.name is None else f": {field_descriptor.name} ({field_descriptor.ref})\n"
            )

            for k, v in sorted(field_descriptor.tags.items()):
                if k == "begin-extensible":  # we indicate cycle len
                    v = [f"cycle length {self.extensible_info[1]}"]
                msg += f"    * {k}: {'; '.join(v)}\n"

        return msg
