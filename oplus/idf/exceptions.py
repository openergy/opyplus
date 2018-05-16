class IdfError(Exception):
    pass


class BrokenIdfError(IdfError):
    pass


class IsPointedError(IdfError):
    pass


class RecordDoesNotExist(IdfError):
    pass


class MultipleRecordsReturned(IdfError):
    pass
