class EpmError(Exception):
    pass


class RecordDoesNotExistError(EpmError):
    pass


class MultipleRecordsReturnedError(EpmError):
    pass


class FieldValidationError(EpmError):
    pass
