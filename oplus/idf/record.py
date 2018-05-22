class Record:
    """
    Record is allowed to access private keys/methods of Idf.
    """
    def __init__(self, record_manager):
        self._ = record_manager

    def __getitem__(self, item):
        """
        Arguments
        ---------
        item: field index or name [or slice of field indexes and/or names]
        """
        if isinstance(item, slice):
            start = 0 if item.start is None else self._.get_field_index(item.start)
            stop = len(self) if item.stop is None else min(self._.get_field_index(item.stop), len(self))
            step = item.step or 1
            return [self._.get_value(i) for i in range(start, stop, step)]
        return self._.get_value(item)

    def get(self, item, default=None):
        try:
            return self[item]
        except (AttributeError, IndexError):
            return default

    def __setitem__(self, key, value):
        """
        Arguments
        ---------
        key: field index or name
        value: field raw, parsed or record value (see get_value documentation)
        """
        self._.set_value(key, value)

    def __len__(self):
        return self._.fields_nb

    def __iter__(self):
        """
        Iter through fields of record.
        """
        return (self[i] for i in range(len(self)))

    def __str__(self):
        return self._.to_str(style="console")

    def __repr__(self):
        name = self._.get_name()
        return f"<{self.table.ref}>" if name is None else f"<{self.table.ref}: {name}>"

    @property
    def idf(self):
        return self._.idf_manager.idf

    @property
    def table(self):
        """
        Record descriptor ref
        """
        return self._.table

    @property
    def pointing_records(self):
        return self._.pointing_records

    @property
    def pointed_records(self):
        return self._.get_pointed_records()

    def unlink_pointing_records(self):
        return self._.unlink_pointing_records()

    def to_str(self, style="idf"):
        return self._.to_str(style=style)

    def info(self, how="txt"):
        """
        Returns a string with all available fields of record (information provided by the idd).

        Arguments
        ---------
        how: str
            txt, dict
        """
        return self._.info(how=how)

    def copy(self):
        return self._.copy()

    def add_field(self, raw_value_or_value, comment=""):
        """
        Add a new field to record (at the end).
        Parameters
        ----------
        raw_value_or_value:
            see get_value for mor information
        comment:
            associated comment
        Returns
        -------
        """
        self._.add_field("", comment=comment)
        self._.set_value(self._.fields_nb-1, raw_value_or_value)

    def replace_values(self, new_record_str):
        """
        Replaces all values of record that are not links (neither pointing nor pointed fields) with values contained
        in the idf record string 'new_record_str'.
        """
        self._.replace_values(new_record_str)

    def pop(self, index=-1):
        """
        Removes field from idf record and shift following rows upwards (value and comment will be removed).
        Can only be applied on extensible fields (for now, only extensible:1).

        Parameters
        ---------
        index: index of field to remove (default -1)

        Returns
        -------
        Value of popped field.
        """
        return self._.pop(index)

    def field_comment(self, field_index_or_name, comment=None):
        if comment is None:
            return self._.get_field_comment(field_index_or_name)
        self._.set_field_comment(field_index_or_name, comment)

    @property
    def head_comment(self):
        return self._.get_head_comment()

    @head_comment.setter
    def head_comment(self, value):
        self._.set_head_comment(value)

    @property
    def tail_comment(self):
        return self._.get_tail_comment()

    @tail_comment.setter
    def tail_comment(self, value):
        self._.set_tail_comment(value)
