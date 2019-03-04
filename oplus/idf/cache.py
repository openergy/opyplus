import itertools


def clear_cache(method):
    def wrapper(self, *args, **kwargs):
        # circular dependencies
        from .idf import Idf
        from .record import Record

        if isinstance(self, Idf):
            idf = self
        elif isinstance(self, Record):
            idf = self._idf
        else:
            raise ValueError("clear_cache decorator applied to a non cached item")
        idf._dev_deactivate_cache()
        res = method(self, *args, **kwargs)
        idf._dev_activate_cache()
        return res
    return wrapper


def cached(method):
    def wrapper(self, *args, **kwargs):
        # circular dependencies
        from .idf import Idf
        from .record import Record

        if isinstance(self, Idf):
            cache = self._dev_cache
        elif isinstance(self, Record):
            cache = self.get_idf()._dev_cache
        else:
            raise ValueError("cached decorator applied to a non cached item")
        if cache is None:
            return method(self, *args, **kwargs)
        key = CacheKey.get(self, method, *args, **kwargs)

        if key not in cache:  # None or not cached yet
            # calculate value
            value = method(self, *args, **kwargs)

            # see if we cache
            if key is None:  # we don't cache
                return value

            # cache
            cache[key] = dict(value=value, hits=0)
        else:
            cache[key]["hits"] += 1
        return cache[key]["value"]
    return wrapper


class CachedMixin:
    _dev_cache = None  # dict(key: dict(value=v, hits=0))  (hits for testing)

    def _dev_activate_cache(self):
        if self._dev_cache is None:
            self._dev_cache = {}

    def _dev_deactivate_cache(self):
        self._dev_cache = None

    def _dev_clear_cache(self):
        if self._dev_cache is not None:
            self._dev_cache = {}

    @property
    def _dev_is_cached(self):
        return self._dev_cache is not None


class CacheKey:
    """
    emulated a dict that can store hashable types
    """
    @classmethod
    def get(cls, obj, method, *args, **kwargs):
        # check that nothing is callable in args or kwargs
        for v in itertools.chain(args, kwargs.values()):
            if callable(v):  # can't cache
                return None
        return cls(obj, method, *args, **kwargs)

    def __init__(self, obj, method,  *args, **kwargs):
        self._value = tuple([obj, method] + list(args) + [(k, v) for k, v in sorted(kwargs.items())])

    def __hash__(self):
        return self._value.__hash__()

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __str__(self):
        return "<CacheKey: %s>" % str(self._value)
