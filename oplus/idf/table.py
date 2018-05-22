from .record import Record


class Table:
    """
    We use this class for api purpose only, but all logic is in idf and records.
    No need to cache table because it uses idf_manager which is cached.
    """
    def __init__(self, ref, idf_manager):
        self._ref = ref
        self._lower_ref = ref.lower()
        self._idf_manager = idf_manager
        self._descriptor = self._idf_manager.idd.get_record_descriptor(ref)

    def __iter__(self):
        return iter(self.select())

    def __len__(self):
        return len(self.select())

    def __repr__(self):
        return f"<Table: {self.ref}>"

    def __str__(self):
        return f"<Table: {self.ref} ({len(self)} records)>"

    def info(self, how="txt"):
        return self._descriptor.info(how=how)

    @property
    def ref(self):
        return self._ref

    def add(self, record_str_s):
        if isinstance(record_str_s, str):
            record_str_s = [record_str_s]
        completed_l = []  # we complete with table ref
        for record_str in record_str_s:
            assert isinstance(record_str, str), f"must provide record string to add record, got {type(record_str)}"
            completed_l.append(f"{self.ref},\n{record_str}")

        return self._idf_manager.add_records(completed_l)

    def remove(self, record_s):
        # make iterable if needed
        if isinstance(record_s, Record):
            record_s = [record_s]

        # check all objects belong to table
        for r in record_s:
            assert r.table.ref == self.ref, \
                f"trying to remove record from other table ({record_s.table_ref}), can't perform removal"

        # ask idf manager to do the job
        self._idf_manager.remove_records(record_s)

    def one(self, filter_by=None):
        return self.select(filter_by=filter_by).one()

    def select(self, filter_by=None):
        # select_all_table is cached
        return self._idf_manager.select_all_table(self._ref).select(filter_by=filter_by)
