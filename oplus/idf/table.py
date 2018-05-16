from .queryset import Queryset
from .record import Record


class Table:
    """
    We use this class for api purpose only, but all logic is in idf and records.
    """
    def __init__(self, ref, idf_manager):
        self._ref = ref
        self._idf_manager = idf_manager

    @property
    def ref(self):
        return self._ref

    def add(self, record_str_s):
        if isinstance(str, record_str_s):
            record_str_s = [record_str_s]
        completed_l = []  # we complete with table ref
        for record_str in record_str_s:
            assert isinstance(record_str, str), f"must provide record string to add record, got {type(record_str)}"
            completed_l.append(f"{self.ref},\n{record_str}")

        self._idf_manager.add(completed_l)

    def select(self, filter_by=None):
        # todo: code
        return Queryset([])

