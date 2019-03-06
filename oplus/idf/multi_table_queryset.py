import itertools
import collections

from .queryset import Queryset


class MultiTableQueryset:
    def __init__(self, idf, records):
        self._idf = idf

        # organize by table (we use ordered dict so __iter__ is deterministic and __eq__ works)
        # to prevent exhausting group iterator too early :
        # 1. we don't sort in groupby
        # 2. we change from iterator to list
        d = {}
        for k, g in itertools.groupby(records, lambda x: x.get_table_ref()):
            _records = list(g)  # change from iterator to list (we need to access first element without breaking group)
            d[k.lower()] = Queryset(_records[0].get_table(), _records)
        self._querysets = collections.OrderedDict(sorted(d.items()))

    def __getattr__(self, item):
        # get table
        table = getattr(self._idf, item)
        table_lower_ref = table.get_ref().lower()

        # return queryset with default if empty
        return self._querysets[table_lower_ref] if table_lower_ref in self._querysets else Queryset(table)

    def __dir__(self):
        """
        Returns
        -------
        only returns non-empty querysets
        """
        return {g[0].get_table_ref() for g in self._querysets.values()}  # all stored querysets have at least 1 element

    def __iter__(self):
        return itertools.chain(*self._querysets.values())

    def __eq__(self, other):
        return set(self) == set(other)
