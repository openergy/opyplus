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
        self._field_descriptors = []  # we use list (and not dict) because some field descriptors do not have a name
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

        # manage corrupt idds
        if self.table_name == "MaterialProperty:GlazingSpectralData":
            cycle_start = 1
            cycle_len = 4
            cycle_patterns = [
                r"wavelength_(\d+)",
                r"transmittance_(\d+)",
                r"front_reflectance_(\d+)",
                r"back_reflectance_(\d+)"
            ]

        elif self.table_name == "Table:MultiVariableLookup":
            cycle_start = 20
            cycle_len = 1
            cycle_patterns = [r"field_(\d+)_determined_by_the_number_of_independent_variables"]

        else:
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
        cycle_start, cycle_len, patterns = self.extensible_info
        for pattern_num, pat in enumerate(patterns):
            match = re.fullmatch(pat, ref)
            if match is None:  # not found
                continue
            # we found cycle
            cycle_num = int(match.group(1))

            # calculate and return index
            return cycle_start + (cycle_num-1)*cycle_len + pattern_num

        raise AttributeError("No field of '%s' has ref '%s'." % (self.table_name, ref))

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

    def get_field_name(self):
        return None if len(self._field_descriptors) == 0 else self._field_descriptors[0].name


    # def get_info(self, how="txt"):
    #     if how not in ("txt", "dict"):
    #         raise ValueError(f"unknown how: '{how}'")
    # 
    #     d = collections.OrderedDict()
    #     for fd in self.field_descriptors:
    #         fields_d = {}
    #         d[fd.name] = fields_d
    #         for tag in fd.tags:
    #             fields_d[tag] = fd.get_tag(tag)
    #     if how == "dict":
    #         return d
    #     msg = "%s\n%s\n%s" % ("-" * len(self.table_ref), self.table_ref, "-" * len(self.table_ref))
    #     for i, (field_name, field_tags) in enumerate(d.items()):
    #         msg += "\n%i: %s" % (i, field_name)
    #         for (tag_name, values) in field_tags.items():
    #             msg += "\n\t* %s: %s" % (tag_name, values)
    #     return msg
