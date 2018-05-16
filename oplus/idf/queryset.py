from .exceptions import RecordDoesNotExist, MultipleRecordsReturned
from .cache import clear_cache


class QuerySet:
    """Contains record, and enables filtering or other operations. Is allowed to access record._."""
    def __init__(self, records):
        self._records = records

    @property
    def records(self):
        return self._records

    def filter(self, field_index_or_name, field_value, condition="="):
        """
        Filter all records who's field value matches field_value according to given condition.

        Arguments
        ---------
        field_index_or_name: field index or name. Can access children with tuple or list.
        field_value_or_values: value on which to be matched.
        condition: "=" (equality)
        condition: 'in' (include in string field)

        Returns
        -------
        QuerySet containing filtered records.
        """
        assert condition in ("=", 'in'), "Unknown condition: '%s'." % condition

        search_tuple = (field_index_or_name,) if isinstance(field_index_or_name, str) else field_index_or_name

        result_l = []
        for o in self._records:
            current_value = o
            for level in search_tuple:
                current_value = current_value._.get_value(level)
            if condition == '=':
                if isinstance(current_value, str) and isinstance(field_value, str):
                    if current_value.lower() == field_value.lower():
                        result_l.append(o)
                elif not isinstance(current_value, type(field_value)):
                    raise ValueError("filter element type %s is not correct" % type(field_value))
                else:
                    if current_value == field_value:
                        result_l.append(o)
            elif condition == 'in':
                if not isinstance(current_value, str):
                    raise ValueError(
                        "condition 'in' can not been performed on field_value  of type %s." % type(field_value))
                if field_value.lower() in current_value.lower():
                    result_l.append(o)
            else:
                raise ValueError("unknown condition : '%s'" % condition)

        return QuerySet(result_l)

    @property
    def one(self):
        """
        Checks that query set only contains one record and returns it.
        """
        if len(self._records) == 0:
            raise RecordDoesNotExist("Query set contains no value.")
        if len(self._records) > 1:
            raise MultipleRecordsReturned("Query set contains more than one value.")
        return self[0]

    def __getitem__(self, item):
        return self._records[item]

    def __iter__(self):
        return iter(self._records)

    def __str__(self):
        return "<QuerySet: %s>" % str(self._records)

    def __call__(self, record_descriptor_ref=None):
        """Returns all records having given record descriptor ref (not case sensitive)."""
        if record_descriptor_ref is None:  # return a copy
            return QuerySet([r for r in self._records])
        return QuerySet([r for r in self._records if r._.ref.lower() == record_descriptor_ref.lower()])

    @clear_cache
    def __add__(self, other):
        """
        Add new query set to query set (only new records will be added).
        """
        self_set = set(self._records)
        other_set = set(other.records)
        intersect_set = self_set.intersection(other_set)
        new_records = []
        new_records.extend(self._records)
        for record in other.records:
            if record not in intersect_set:
                new_records.append(record)
        return QuerySet(new_records)

    def __len__(self):
        return len(self._records)

