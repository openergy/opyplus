from itertools import filterfalse

from .exceptions import RecordDoesNotExistError, MultipleRecordsReturnedError
from .cache import clear_cache


def unique_ever_seen(iterable, key=None):
    """
    https://docs.python.org/3.6/library/itertools.html#itertools-recipes
    List unique elements, preserving order. Remember all elements ever seen.

    unique_ever_seen('AAAABBBCCDAABBB') --> A B C D
    unique_ever_seen('ABBCcAD', str.lower) --> A B C D
    """
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


class Queryset:
    """
    Contains record, and enables filtering or other operations.
    A queryset must be immutable (not a Python sense, but list must never be modified). OR CACHE SYSTEM WILL FAIL.
    We only use lists (and not iterators), to avoid problems (could be done if optimization was needed):
        - exhaustion
        - iterator underlying list modification

    Optimization can probably be performed using iterators.
    """
    def __init__(self, table, records=None):
        self._table = table

        # manage empty
        if records is None:
            records = []

        # ensure unique
        self._records = list(unique_ever_seen(records))  # !! MUST NEVER BE MODIFIED !!

        # ensure correct table ref
        if len({r.get_table() for r in self._records}.difference({self._table})) > 0:
            raise RuntimeError(
                f"queryset contains records that belong to other table than {self.get_table_ref()}"
            )

    def get_table(self):
        return self._table

    def get_table_ref(self):
        return self._table.get_ref()

    def select(self, filter_by=None):
        """
        select a sub queryset
        """
        # !! we copy list so it can't change in the future !!
        iterator = list(self._records) if filter_by is None else list(filter(filter_by, self._records))
        return Queryset(self._table, iterator)

    def one(self, filter_by=None):
        """
        Checks that query set only contains one record and returns it.
        """
        # filter if needed
        qs = self if filter_by is None else self.select(filter_by=filter_by)

        # check one and only one
        if len(qs) == 0:
            raise RecordDoesNotExistError("Queryset set contains no value.")
        if len(qs) > 1:
            raise MultipleRecordsReturnedError("Queryset contains more than one value.")

        # return record
        return qs[0]

    def __getitem__(self, item):
        return self._records[item]

    def __iter__(self):
        return iter(self._records)

    def __str__(self):
        return "<Queryset of %s: %s items>" % (self.get_table_ref(), str(len(self._records)))

    def __len__(self):
        return len(self._records)

    @clear_cache
    def __add__(self, other):
        """
        Add new query set to query set (only new records will be added since uniqueness is ensured in __init__).
        """
        if self._table is not other.get_table():
            raise RuntimeError("can't add two querysets that don't belong to same table")
        return Queryset(list(self) + list(other))
