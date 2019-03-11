class EpmError(Exception):
    pass


class BrokenEpmError(EpmError):
    pass


class IsPointedError(EpmError):
    pass


class RecordDoesNotExistError(EpmError):
    pass


class MultipleRecordsReturnedError(EpmError):
    pass


class ObsoleteRecordError(EpmError):
    pass
