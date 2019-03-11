def get_documented_add(record_descriptors):
    """
    this hack is used to document add function
    a methods __doc__ attribute is read-only (or must use metaclasses, what I certainly don't want to do...)
    we therefore create a function (who's __doc__ attribute is read/write), and will bind it to Table in __init__
    """
    def add(self, **record_data):
        return self.get_epm().add(self.get_ref(), **record_data)
    add.__doc__ = "\n".join([fd.ref.lower() for fd in record_descriptors if fd.ref is not None])
    return add


class Table:
    """
    We use this class for api purpose only, but all logic is in idf and records.
    No need to cache table because it uses idf_manager which is cached.
    """
    def __init__(self, record_descriptor, idf):
        self._ref = record_descriptor.table_ref
        self._idf = idf
        self._descriptor = record_descriptor
        self.add = get_documented_add(record_descriptor.field_descriptors)

    # python magic
    def __iter__(self):
        return iter(self.select())

    def __getitem__(self, item):
        return self.select()[item]

    def __len__(self):
        return len(self.select())

    def __repr__(self):
        return f"<Table: {self.get_ref()}>"

    def __str__(self):
        return f"<Table: {self.get_ref()} ({len(self)} records)>"

    # structure info
    def get_idf(self):
        return self._idf

    def get_ref(self):
        return self._ref

    # add records
    # def add(self, **record_data): was monkey patched in init with appropriate docstring

    def batch_add(self, records_data):
        """
        Parameters
        ----------
        records_data: list of records data

        Returns
        -------
        list of created records
        """
        return self.get_idf().batch_add({self.get_ref(): records_data})

    def add_from_string(self, record_str):
        return self.batch_add_from_string([record_str])

    def batch_add_from_string(self, records_str):
        completed_l = []  # we complete with table ref
        for record_str in records_str:
            assert isinstance(record_str, str), f"must provide record string to add record, got {type(record_str)}"
            completed_l.append(f"{self.get_ref()},\n{record_str}")

        return self._idf.batch_add_from_string(completed_l)

    # remove records
    def remove(self, record):
        self.batch_remove([record])

    def batch_remove(self, records):
        # check all objects belong to table
        if {r.get_table_ref() for r in records} != {self.get_ref()}:
            raise RuntimeError(
                    f"trying to remove record from other tables than '{self.get_ref()}', can't perform removal."
                )

        # ask idf manager to do the job
        self._idf.remove_records(records)

    # selection
    def one(self, filter_by=None):
        return self.select(filter_by=filter_by).one()

    def select(self, filter_by=None):
        # select_all_table is cached
        return self._idf._dev_select_from_table(self._ref).select(filter_by=filter_by)

    # info
    def get_info(self, how="txt"):
        return self._descriptor.get_info(how=how)