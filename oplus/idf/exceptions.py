class IdfError(Exception):
    pass


class BrokenIdfError(IdfError):
    pass


class IsPointedError(IdfError):
    pass


class RecordDoesNotExistError(IdfError):
    pass


class MultipleRecordsReturnedError(IdfError):
    pass


class ObsoleteRecordError(IdfError):
    pass
