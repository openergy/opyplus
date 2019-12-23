import itertools
import collections

from .queryset import Queryset


class MultiTableQueryset:
    def __init__(self, epm, records):
        self._epm = epm

        # organize by table (we use ordered dict so __iter__ is deterministic and __eq__ works)
        # to prevent exhausting group iterator too early :
        # 1. we don't sort in groupby
        # 2. we change from iterator to list
        d = {}
        # we sort records because groupby only groups consecutive items
        for k, g in itertools.groupby(sorted(records), lambda x: x.get_table_ref()):
            _records = list(g)  # change from iterator to list (we need to access first element without breaking group)
            d[k.lower()] = Queryset(_records[0].get_table(), _records)
        self._querysets = collections.OrderedDict(sorted(d.items()))

    # python magic
    def __getattr__(self, item):
        # get table
        table = getattr(self._epm, item)
        table_lower_ref = table.get_ref().lower()

        # return queryset with default if empty
        return self._querysets[table_lower_ref] if table_lower_ref in self._querysets else Queryset(table)

    def __dir__(self):
        """
        Returns
        -------
        only returns non-empty querysets
        """
        # all stored querysets have at least 1 element
        return [g[0].get_table_ref() for g in self._querysets.values()] + list(self.__dict__)

    def __iter__(self):
        return iter(self._querysets)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise ValueError("can only compare a queryset with another queryset")
        return set(self.iter_all_records()) == set(other.iter_all_records())

    def __len__(self):
        # works with 0 (checked)
        return len(self._querysets)

    def items(self):
        return self._querysets.items()

    def keys(self):
        return self._querysets.keys()

    def values(self):
        return self._querysets.values()

    def iter_all_records(self):
        return itertools.chain(*self._querysets.values())
