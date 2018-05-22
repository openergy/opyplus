import collections


class RecordDescriptor:
    """
    Describes a EPlus record (see idd).
    """
    def __init__(self, table_ref, group_name=None):
        self.table_ref = table_ref
        self.group_name = group_name
        self._fieldds_l = []
        self._tags_d = {}

        # extensible management
        self._extensible_cycle_len = 0  # if 0: not extensible
        self._extensible_cycle_start = None  # will be filled first time asked

    @property
    def tags(self):
        return sorted(self._tags_d)

    @property
    def field_descriptors_l(self):
        return self._fieldds_l

    def get_tag(self, ref):
        """
        Returns tag belonging to record descriptor. If 'memo', will be string, else list of elements.
        """
        if ref == "memo":  # note if for field descriptors
            return " ".join(self._tags_d[ref])
        return self._tags_d[ref]

    def add_tag(self, ref, value=None):
        if value is None:
            return None

        if ref not in self._tags_d:
            self._tags_d[ref] = []
        self._tags_d[ref].append(value)

        # manage extensible
        if "extensible" in ref:
            self._extensible_cycle_len = int(ref.split(":")[1])

    def add_field_descriptor(self, field):
        """
        Adds a new field descriptor.
        """
        self._fieldds_l.append(field)

    def get_field_descriptor(self, index_or_name):
        """
        Returns
        -------
        asked field descriptor.
        """
        index = self.get_field_index(index_or_name)

        if index >= len(self._fieldds_l) and (self._extensible_cycle_len != 0):  # extensible record, find modulo
            index = self._extensible_cycle_len + ((index - self._extensible_cycle_start) % self._extensible_cycle_len)

        return self._fieldds_l[index]

    def get_field_index(self, index_or_insensitive_name):
        """
        if index, must be >=0
        """
        # if index
        if isinstance(index_or_insensitive_name, int):
            if index_or_insensitive_name >= len(self._fieldds_l) and (self._extensible_cycle_len == 0):
                raise IndexError("Index out of range : %i." % index_or_insensitive_name)
            return index_or_insensitive_name

        # if name (extensible can not be used here)
        lower_name = index_or_insensitive_name.lower()
        for i, cur_field in enumerate(self._fieldds_l):
            if cur_field.name.lower() == lower_name:
                return i
        raise AttributeError("No field of '%s' is named '%s'." % (self.table_ref, index_or_insensitive_name))

    def get_field_name(self, index):
        return None if len(self._fieldds_l) == 0 else self._fieldds_l[0].name
    #
    # @property
    # def formatted_ref(self):
    #     return self.ref.replace(":", "_")

    @property
    def extensible(self):
        """
        Returns cycle_len, cycle_start
        """
        if self._extensible_cycle_len == 0:
            return None, None
        if self._extensible_cycle_start is None:
            for i, fieldd in enumerate(self._fieldds_l):
                if fieldd.has_tag("begin-extensible"):
                    break
            else:
                raise KeyError("begin-extensible tag not found.")
            self._extensible_cycle_start = i
        return self._extensible_cycle_len, self._extensible_cycle_start

    def info(self, how="txt"):
        assert how in ("txt", "dict")
        d = collections.OrderedDict()
        for fd in self.field_descriptors_l:
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
