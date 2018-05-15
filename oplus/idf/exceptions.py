class IdfError(Exception):
    pass


class BrokenIdfError(IdfError):
    pass


class IsPointedError(IdfError):
    pass


class ObjectDoesNotExist(IdfError):
    pass


class MultipleObjectsReturned(IdfError):
    pass
