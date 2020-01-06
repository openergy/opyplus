"""Opyplus public exceptions."""

__all__ = ["RecordDoesNotExistError", "MultipleRecordsReturnedError", "FieldValidationError",
           "DatetimeInstantsCreationError"]


class RecordDoesNotExistError(Exception):
    """Record does not exist exception."""

    pass


class MultipleRecordsReturnedError(Exception):
    """Exception when more than one record is returned and only one was expected."""

    pass


class FieldValidationError(Exception):
    """Exception when field validation fails."""

    pass


class DatetimeInstantsCreationError(Exception):
    """Exception when datetime instants creation fails."""

    pass
