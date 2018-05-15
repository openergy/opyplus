from .exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from .cache import clear_cache


class QuerySet:
    """Contains object, and enables filtering or other operations. Is allowed to access object._."""
    def __init__(self, objects_l):
        self._objects_l = objects_l

    @property
    def objects_l(self):
        return self._objects_l

    def filter(self, field_index_or_name, field_value, condition="="):
        """
        Filter all objects who's field value matches field_value according to given condition.
        Arguments
        ---------
        field_index_or_name: field index or name. Can access children with tuple or list.
        field_value_or_values: value on which to be matched.
        condition: "=" (equality)
        condition: 'in' (include in string field)
        Returns
        -------
        QuerySet containing filtered objects.
        """
        assert condition in ("=", 'in'), "Unknown condition: '%s'." % condition

        search_tuple = (field_index_or_name,) if isinstance(field_index_or_name, str) else field_index_or_name

        result_l = []
        for o in self._objects_l:
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
        Checks that query set only contains one object and returns it.
        """
        if len(self._objects_l) == 0:
            raise ObjectDoesNotExist("Query set contains no value.")
        if len(self._objects_l) > 1:
            raise MultipleObjectsReturned("Query set contains more than one value.")
        return self[0]

    def __getitem__(self, item):
        return self._objects_l[item]

    def __iter__(self):
        return iter(self._objects_l)

    def __str__(self):
        return "<QuerySet: %s>" % str(self._objects_l)

    def __call__(self, object_descriptor_ref=None):
        """Returns all objects having given object descriptor ref (not case sensitive)."""
        if object_descriptor_ref is None:  # return a copy
            return QuerySet([o for o in self._objects_l])
        return QuerySet([o for o in self._objects_l if o._.ref.lower() == object_descriptor_ref.lower()])

    @clear_cache
    def __add__(self, other):
        """
        Add new query set to query set (only new objects will be added).
        """
        self_set = set(self._objects_l)
        other_set = set(other.objects_l)
        intersect_set = self_set.intersection(other_set)
        new_objects_l = []
        new_objects_l.extend(self._objects_l)
        for idf_object in other.objects_l:
            if idf_object not in intersect_set:
                new_objects_l.append(idf_object)
        return QuerySet(new_objects_l)

    def __len__(self):
        return len(self._objects_l)

