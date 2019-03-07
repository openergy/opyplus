import uuid
import io

from ..configuration import CONF
from .exceptions import ObsoleteRecordError, IsPointedError, BrokenIdfError
from .cache import CachedMixin, clear_cache, cached
from .style import style_library, IdfStyle
from .multi_table_queryset import MultiTableQueryset


class Record:
    _frozen = False  # for __setattr__ management

    def __init__(self, table, data=None, comments=None, head_comment=None, tail_comment=None):
        """
        Parameters
        ----------
        table
        data: dict, default {}
            key: index_or_ref, value: raw value or value
        comments: dict, default {}
            key: index_or_ref, value: raw value or value
        head_comment: str, default ""
        tail_comment: str, default ""
        """
        self._table = table
        self._data = {} if data is None else data
        self._comments = {} if comments is None else comments
        self._head_comment = "" if head_comment is None else str(head_comment)
        self._tail_comment = "" if tail_comment is None else str(tail_comment)
        
        # todo: perform data checks

        self._frozen = True

    def _dev_activate_links(self):
        pass
        # todo: iter all data, if is Link, activate it

    def get_pk(self):
        """
        Returns
        -------
        python id if auto pk, else pk
        """
        return id(self) if self._table._dev_auto_pk else self[0]
    
    def __getitem__(self, item):
        return self._data[0]
    
    def __setitem__(self, key, value):
        pass
        # todo: don't forget to notify pk update
    
    def __setattr__(self, key, value):
        pass
        # todo: don't forget to notify pk update   
