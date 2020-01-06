"""Epm queryset module."""

from itertools import filterfalse

from ..exceptions import RecordDoesNotExistError, MultipleRecordsReturnedError


def _unique_ever_seen(iterable, key=None):
    """
    List unique elements, preserving order. Remember all elements ever seen.

    https://docs.python.org/3.6/library/itertools.html#itertools-recipes

    >>> list(_unique_ever_seen('AAAABBBCCDAABBB'))
    ['A', 'B', 'C', 'D']
    >>> list(_unique_ever_seen('ABBCcAD', str.lower))
    ['A', 'B', 'C', 'D']
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

    Parameters
    ----------
    table: opyplus.epm.table.Table
    records: typing.Iterable[opyplus.epm.record.Record]
    """

    def __init__(self, table, records=None):
        self._table = table

        # manage empty
        if records is None:
            records = ()

        # ensure unique, sort, make un-mutable
        self._records = tuple(sorted(_unique_ever_seen(records)))

        # ensure correct table
        if len({r.get_table() for r in self._records}.difference({self._table})) > 0:
            raise RuntimeError(
                f"queryset contains records that belong to other table than {self.get_table_ref()}"
            )

    # python magic
    def __repr__(self):
        """
        Get the string representation of a record.

        Returns
        -------
        str
        """
        return "<Queryset of %s: %s records>" % (self.get_table_ref(), str(len(self._records)))

    def __getitem__(self, item):
        """
        Get record(s) from the queryset by index/slice.

        Parameters
        ----------
        item: int or slice
            record(s) position(s) (records are ordered by their content, not by creation order)

        Returns
        -------
        opyplus.epm.record.Record
        """
        return self._records[item]

    def __iter__(self):
        """
        Iterate through the records.

        Returns
        -------
        typing.Iterator[opyplus.epm.record.Record]
        """
        return iter(self._records)

    def __len__(self):
        """
        Get the number of records in the queryset.

        Returns
        -------
        int
        """
        return len(self._records)

    def __add__(self, other):
        """
        Add new query set to query set (only new records will be added since uniqueness is ensured in __init__).

        Parameters
        ----------
        other: Queryset

        Returns
        -------
        bool
        """
        return Queryset(self._table, list(self) + list(other))

    def __eq__(self, other):
        """
        Check if two queryset are equal (contain the same records).

        Parameters
        ----------
        other: Queryset

        Returns
        -------
        bool
        """
        return set(self) == set(other)

    # get info
    def get_table(self):
        """
        Get this queryset table.

        Returns
        -------
        opyplus.epm.table.Table
        """
        return self._table

    def get_table_ref(self):
        """
        Get this queryset table ref.

        Returns
        -------
        str
        """
        return self._table.get_ref()

    def select(self, filter_by=None):
        """
        Select records from this queryset using a given filter function.

        Parameters
        ----------
        filter_by: typing.Callable or None
            if None (default): select all records in the queryset.
            Callable must take one argument (a record of queryset), and return True to keep it, or False to skip it.
            Example: .select(lambda x: x.name == "my_name").
        If None, records are not filtered.

        Returns
        -------
        Queryset instance, containing all selected records.
        """
        iterator = self._records if filter_by is None else filter(filter_by, self._records)
        return Queryset(self._table, iterator)

    def one(self, filter_by=None):
        """
        Select a single record from this queryset using a filter function. If more than one record is filtered, raises.

        Parameters
        ----------
        filter_by: callable, default None
            Callable must take one argument (a record of table), and return True to keep record, or False to skip it.
            Example : .one(lambda x: x.name == "my_name").
            If None, records are not filtered.

        Returns
        -------
        opyplus.epm.record.Record
            If one and only one record is found. Else raises.

        Raises
        ------
        RecordDoesNotExistError
            if no record is found
        MultipleRecordsReturnedError
            if multiple records are found
        """
        # filter if needed
        if isinstance(filter_by, str):
            if self._table._dev_no_pk:
                raise KeyError(f"table {self._table.get_ref()} does not have a primary key, can't use getitem syntax")
            for r in self._records:  # later: we could store records in an ordered dict with id keys
                if r.id == filter_by:
                    return r
            raise RecordDoesNotExistError(f"queryset does not contain a record who's id is '{filter_by}'")

        qs = self if filter_by is None else self.select(filter_by=filter_by)

        # check one and only one
        if len(qs) == 0:
            raise RecordDoesNotExistError("Queryset set contains no value.")
        if len(qs) > 1:
            raise MultipleRecordsReturnedError("Queryset contains more than one value.")

        # return record
        return qs[0]

    # delete
    def delete(self):
        """Delete all records in this queryset."""
        # workflow
        # --------
        # delete each record and remove from queryset

        # delete each record
        for r in self:
            r.delete()

        # clear content
        self._records = ()

    # ------------------------------------------- export ---------------------------------------------------------------
    def to_json_data(self):
        """
        Queryset as a json-serializable list.

        Returns
        -------
        list
        """
        # records are already sorted
        return [r.to_json_data() for r in self._records]
