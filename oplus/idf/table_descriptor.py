import collections
import logging

logger = logging.getLogger(__name__)


def table_name_to_ref(name):
    return name.replace(":", "_")


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
        # (cycle_start, cycle_len, patterns) where patterns is (var_a_{cycle}_ref, var_b_{cycle}_ref, ...)
        self._extensible_info = None

    def post_init(self):
        """
        This function finishes initialization, must be called once all field descriptors and tag have been filled.
        """
        # manage extensible
        for k in self._tags:
            if "extensible" in k:
                cycle_len = int(k.split(":")[1])
                break
        else:
            # not extensible
            self._extensible_info = None, None, None
            return

        # find cycle start and prepare patterns
        cycle_start = None
        cycle_patterns = []
        for i, field_descriptor in enumerate(self._field_descriptors):
            # quit if finished
            if (cycle_start is not None) and (i >= (cycle_start + cycle_len)):
                break

            # set cycle start if not set yet
            if (cycle_start is None) and field_descriptor.has_tag("begin-extensible"):
                cycle_start = i

            # leave if cycle start not reached yet
            if cycle_start is None:
                continue

            # store pattern

            # hack 1: manage idd wrong cycle len bug
            if field_descriptor.ref is None:
                # idd sometimes uses extensible:n but it is in fact extensible:1.
                # we patch here to correct this error
                if len(cycle_patterns) != 1:
                    raise RuntimeError("patch only works if one and only one pattern has been stored")
                # change cycle len
                cycle_len = 1
                # log
                logger.info(
                    "idd wrong cycle len, automatic correction was applied",
                    extra=dict(table_name=self.table_name)
                )
                # leave
                break

            # hack 2: manage idd wrong cycle_start bug
            if "1" not in field_descriptor.ref:
                # identify correct number (try up to 5)
                for c in "2345":
                    if c in field_descriptor.ref:
                        break
                else:
                    raise RuntimeError("wrong cycle_start idd bug could not be automatically corrected, aborting")

                # create ref that will be looked for in previous field descriptors
                previous_ref = field_descriptor.ref.replace(c, "1")
                for previous_i, previous_fieldd in enumerate(self._field_descriptors[:i]):
                    if previous_fieldd.ref == previous_ref:  # found
                        break
                else:
                    raise RuntimeError("wrong cycle_len idd bug could not be automatically corrected, aborting")

                # change cycle_start and force cycle_len and cycle_patterns
                cycle_start = previous_i
                cycle_len = 1
                cycle_patterns = [previous_ref.replace("1", "{cycle}")]  # todo: this should be a regex

                # log
                logger.info(
                    "idd wrong cycle start, automatic correction was applied",
                    extra=dict(table_name=self.table_name)
                )

                # leave
                break

            # manage correct case
                # raise RuntimeError(f"1 not found, can't create pattern: '{field_descriptor.ref}'")
            cycle_patterns.append(field_descriptor.ref.replace("1", "{cycle}"))
        else:
            raise RuntimeError("cycle start not found")

        # detach unnecessary field descriptors
        self._field_descriptors = self.field_descriptors[:cycle_start + cycle_len]

        # store cycle info
        self._extensible_info = (cycle_start, cycle_len, tuple(cycle_patterns))

    @property
    def tags(self):
        return sorted(self._tags)

    @property
    def field_descriptors(self):
        return self._field_descriptors

    def get_tag(self, tag_ref, raw=False):
        """
        Returns tag belonging to record descriptor. If 'memo', will be string, else list of elements.
        """
        if tag_ref == "memo" and not raw:  # note if for field descriptors
            return " ".join(self._tags[tag_ref])
        return self._tags[tag_ref]

    def add_tag(self, tag_ref, value=None):
        if tag_ref not in self._tags:
            self._tags[tag_ref] = []
        if value is not None:
            self._tags[tag_ref].append(value)

    def append_field_descriptor(self, field_descriptor):
        """
        Adds a new field descriptor.
        """
        # append
        self._field_descriptors.append(field_descriptor)

    def get_field_descriptor(self, index):
        """
        Returns
        -------
        asked field descriptor.
        """
        if index >= len(self._field_descriptors) and (self._extensible_info[0] is not None):  # extensible record, find modulo
            cycle_start, cycle_len, _ = self._extensible_info
            index = cycle_start + ((index - cycle_start) % cycle_len)

        return self._field_descriptors[index]

    def get_field_index(self, index_or_ref):
        """
        if index, must be >=0

        Raises
        ------
        AttributeError
        """
        # if index
        if isinstance(index_or_ref, int):
            if index_or_ref >= len(self._field_descriptors) and (self._extensible_info[0] is None):
                raise IndexError("Index out of range : %i." % index_or_ref)
            return index_or_ref

        # if name (extensible can not be used here)
        for i, cur_field in enumerate(self._field_descriptors):
            if cur_field.ref is None:  # can happen, for example if extensible...
                continue
            if cur_field.ref == index_or_ref:
                return i
        raise AttributeError("No field of '%s' has ref '%s'." % (self.table_name, index_or_ref))

    def get_field_name(self):
        return None if len(self._field_descriptors) == 0 else self._field_descriptors[0].name

    @property
    def extensible_info(self):
        """
        Returns (cycle_len, cycle_start, patterns) or (None, None, None) if not extensible
        """
        return self._extensible_info

    def get_info(self, how="txt"):
        if how not in ("txt", "dict"):
            raise ValueError(f"unknown how: '{how}'")

        d = collections.OrderedDict()
        for fd in self.field_descriptors:
            fields_d = {}
            d[fd.name] = fields_d
            for tag in fd.tags:
                fields_d[tag] = fd.get_tag(tag)
        if how == "dict":
            return d
        msg = "%s\n%s\n%s" % ("-" * len(self.table_ref), self.table_ref, "-" * len(self.table_ref))
        for i, (field_name, field_tags) in enumerate(d.items()):
            msg += "\n%i: %s" % (i, field_name)
            for (tag_name, values) in field_tags.items():
                msg += "\n\t* %s: %s" % (tag_name, values)
        return msg

    def __eq__(self, other):
        """ Eq between two RecordDescriptor instances """
        assert isinstance(other, TableDescriptor), "other should be a RecordDescriptor instance"

        if self.table_ref != other.table_ref:
            return False
        elif self.group_name != other.group_name:
            return False
        elif (
                len(self._tags) != len(other._tags)
                or sorted(self._tags.items()) != sorted(other._tags.items())
        ):
            return False
        elif (
                len(self.field_descriptors) != len(other.field_descriptors)
                or any([f1 != f2 for f1, f2 in zip(self.field_descriptors, other.field_descriptors)])
        ):
            return False
        else:
            return True
