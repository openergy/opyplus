"""
Idf
---
We respect private/public naming conventions for methods and variables, EXCEPT for Idf or IdfObject managers. The
_manager variable is semi-private: it can be accessed by other managers (including other modules of oplus), but not by
Idf or IdfObject. The _manager attributes therefore remain private to oplus users.
"""
from contextlib import contextmanager
from .idf_manager import IdfManager


class Idf:
    """
    Idf is allowed to access private keys/methods of IdfObject.
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

    def remove_object(self, object_to_remove, raise_if_pointed=True):  # todo: remove (now __del__ on record)
        """
        Removes object from idf.
        Arguments
        ---------
        object_to_remove: object to remove
        raise_if_pointed: check if links have been broken.
            If check is True and broken links are detected, will raise an IdfError
            (nodes or branches checking has not been implemented).
        """
        return self._.remove_object(object_to_remove, raise_if_pointed=raise_if_pointed)

    def add_object(self, new_str, position=None): # todo: change (now add on table)
        """
        Adds new object to the idf, at required position.
        Arguments
        ---------
        new_or_str: new object (or string describing new object) that will be added to idf
        position: if None, will be added at the end, else will be added at asked position
            (using 'insert' python builtin function for lists)
        check: check if pointed objects of new object exists. If check is True and a non existing link is detected, will
            raise an IdfError
        """
        return self._.add_object(new_str, position=position)

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
