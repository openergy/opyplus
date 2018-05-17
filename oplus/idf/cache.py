import itertools


def clear_cache(method):
    def wrapper(self, *args, **kwargs):
        # circular dependencies
        from .idf_manager import IdfManager
        from .record_manager import RecordManager

        if isinstance(self, IdfManager):
            idf_manager = self
        elif isinstance(self, RecordManager):
            idf_manager = self.idf_manager
        else:
            raise ValueError("clear_cache decorator applied to a non cached item")
        idf_manager.deactivate_cache()
        res = method(self, *args, **kwargs)
        idf_manager.activate_cache()
        return res
    return wrapper


def cached(method):
    def wrapper(self, *args, **kwargs):
        # circular dependencies
        from .idf_manager import IdfManager
        from .record_manager import RecordManager

        if isinstance(self, IdfManager):
            cache = self.cache
        elif isinstance(self, RecordManager):
            cache = self.idf_manager.cache
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


class Cached:
    cache = None  # dict(key: dict(value=v, hits=0))  (hits for testing)

    def activate_cache(self):
        if self.cache is None:
            self.cache = {}

    def deactivate_cache(self):
        self.cache = None

    def clear_cache(self):
        if self.cache is not None:
            self.cache = {}

    @property
    def is_cached(self):
        return self.cache is not None


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
