"""
Idf
---
We respect private/public naming conventions for methods and variables, EXCEPT for Idf or Record managers. The
_manager variable is semi-private: it can be accessed by other managers (including other modules of oplus), but not by
Idf or Record. The _manager attributes therefore remain private to oplus users.
"""
from contextlib import contextmanager
from .idf_manager import IdfManager


class Idf:
    """
    Idf is allowed to access private keys/methods of Record.
    """
    idf_manager_cls = IdfManager  # for subclassing

    @classmethod
    def get_idf(cls, idf_or_path, encoding=None):
        """
        Arguments
        ---------
        idf_or_path: idf record or idf file path
        encoding

        Returns
        -------
        Idf record
        """
        if isinstance(idf_or_path, str):
            return cls(idf_or_path, encoding=encoding)
        elif isinstance(idf_or_path, cls):
            return idf_or_path
        raise ValueError(
            "'idf_or_path' must be a path or an Idf. Given object: '{idf_or_path}', type: '{type(idf_or_path)}'."
        )

    def __init__(self, path_or_content, idd_or_path=None, encoding=None, style=None):
        """
        Arguments
        ---------
        path_or_content: idf path, content str, content bts or file_like. If path, must end by .idf.
        idd_or_path: Idd record or idd path. If None, default will be chosen (most recent EPlus version installed on
            computer)
        """
        self._ = self.idf_manager_cls(
            self,
            path_or_content,
            idd_or_path=idd_or_path,
            encoding=encoding,
            style=style
        )

    def __call__(self, record_descriptor_ref=None):
        """returns all records of given record descriptor"""
        return self._.filter_by_ref(record_descriptor_ref)

    def to_str(self, add_copyright=True):
        return self._.to_str(add_copyright=add_copyright)

    def save_as(self, file_or_path, style=None, clean=False):
        self._.save_as(file_or_path, style=style, clean=clean)

    def copy(self, add_copyright=True):
        return self._.copy(add_copyright=add_copyright)

    def add(self, new_record_str, position=None):
        """
        Adds new record to the idf, at required position.

        Arguments
        ---------
        new_record_str: string describing the new record that will be added to idf
        position: if None, will be added at the end, else will be added at asked position
            (using 'insert' python builtin function for lists)
        position
        """
        return self._.add_record(new_record_str, position=position)

    def remove(self, record):
        """
        removes record from idf.
        This record must not be pointed by other records, or removal will fail

        Parameters
        ----------
        record

        Raises
        ------
        IsPointedError
        """
        self._.remove_record(record)

    def info(self, sort_by_group=False, detailed=False):
        """
        Arguments
        ---------
        sort_by_group: will sort record descriptors by group
        detailed: will give all record descriptors' associated tags
        Returns
        -------
        a text describing the information on record contained in idd file
        """
        return self._.info(sort_by_group=sort_by_group, detailed=detailed)

    @property
    def comment(self):
        return self._.get_comment()

    @comment.setter
    def comment(self, value):
        self._.set_comment(value)

    def clear_cache(self):
        self._.clear_cache()

    @property
    @contextmanager
    def under_construction(self):
        with self._.under_construction:
            yield
