import uuid
import io

from ..configuration import CONF
from .exceptions import ObsoleteRecordError, IsPointedError, BrokenIdfError
from .cache import CachedMixin, clear_cache, cached
from .style import style_library, IdfStyle
from .multi_table_queryset import MultiTableQueryset
from .link import Link
from .hook import Hook


class Record:
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
        
        # todo: check data and comments

    def _dev_set_value_inert(self, field_index_or_ref, value):
        """
        inert: links and hooks will not be activated
        """
        
        # prepare index
        index = self._table._dev_descriptor.get_field_index(field_index_or_ref)
        
        # get field descriptor
        field_descriptor = self._table._dev_descriptor.get_field_descriptor(index)
        
        # prepare value
        value = field_descriptor.deserialize(value)

        # manage if link
        if isinstance(value, Link):
            # de-activate current link if any
            current_link = self._data.get(index)
            if current_link is not None:
                current_link.deactivate()
                
        # manage if hook
        if isinstance(value, Hook):
            current_hook = self._data.get(index)
            if current_hook is not None:
                current_hook.deactivate()
                
        # if None check ok and remove
        if value is None:
            # todo: check if ok
            
            # remove
            del self._data[index]
        
        # else remove
        else:
            self._data[index] = value
            
    def _dev_activate_hooks(self):
        pass
        # todo: iter all data, if is Link, activate it

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
    
    def __setattr__(self, name, value):
        try:
            super().__setattr__(name, value)
            return
        except AttributeError:
            pass

        pass
        # todo: don't forget to notify pk update   
