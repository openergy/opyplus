__all__ = ["RecordDoesNotExistError", "MultipleRecordsReturnedError", "FieldValidationError",
           "DatetimeInstantsCreationError"]


class RecordDoesNotExistError(Exception):
    pass


class MultipleRecordsReturnedError(Exception):
    pass


class FieldValidationError(Exception):
    pass


class DatetimeInstantsCreationError(Exception):
    pass
