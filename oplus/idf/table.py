from .queryset import Queryset
from .record import Record


# todo: cache table
class Table:
    """
    We use this class for api purpose only, but all logic is in idf and records.
    """
    def __init__(self, ref, idf_manager):
        self._lower_ref = ref.lower()
        self._idf_manager = idf_manager

    @property
    def ref(self):
        return self._lower_ref

    def add(self, record_str_s):
        if isinstance(str, record_str_s):
            record_str_s = [record_str_s]
        completed_l = []  # we complete with table ref
        for record_str in record_str_s:
            assert isinstance(record_str, str), f"must provide record string to add record, got {type(record_str)}"
            completed_l.append(f"{self.ref},\n{record_str}")

        self._idf_manager.add(completed_l)

    def remove(self, record_s):
        # make iterable if needed
        if isinstance(record_s, Record):
            record_s = [record_s]

        # check all objects belong to table
        for r in record_s:
            assert r.table.ref == self.ref, \
                f"trying to remove record from other table ({record_s.table.ref}), can't perform removal"

        # ask idf manager to do the job
        self._idf_manager.remove_records(record_s)

    def one(self, filter_by=None):
        return self.select(filter_by=filter_by).one()

    def select(self, filter_by=None):
        return self._idf_manager.select(
            filter_by=lambda x: x.table.ref == self._lower_ref
        ).select(
            filter_by=filter_by
        )
