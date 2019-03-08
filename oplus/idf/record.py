import uuid
import io
import collections

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
    
    def _get_fields_nb(self):
        return max(max(self._data), len(self._table._dev_descriptor.field_descriptors))

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
    
    def to_json_data(self):
        values = collections.OrderedDict(
            sorted([(k, v.serialize() if isinstance(v, (Link, Hook)) else v) for k, v in self._data.items()])
        )
        comments = collections.OrderedDict(sorted(self._comments.items()))
        return collections.OrderedDict(
            data=values,
            comments=comments,
            head_comment=self._head_comment,
            tail_comment=self._tail_comment
        )
    
    def to_str(self, style="idf", idf_style=None):
        # todo: manage obsolescence ?
        #  self._check_obsolescence()
        json_data = self.to_json_data()
        
        if style not in ("idf", "console"):
            raise AttributeError("Unknown style: '%s'." % style)

        # prepare styling
        if idf_style is None:
            idf_style = style_library[CONF.default_write_style]
        if isinstance(idf_style, IdfStyle):
            idf_style = idf_style
        elif isinstance(idf_style, str):
            if idf_style in style_library.keys():
                idf_style = style_library[style]
            else:
                idf_style = style_library[CONF.default_write_style]
        else:
            idf_style = style_library[CONF.default_write_style]
            
        # record descriptor ref
        content = f"{self._table._dev_descriptor.table_name},"
        spaces_nb = idf_style.comment_column_start - len(content)
        if spaces_nb < 0:
            spaces_nb = idf_style.tab_len

        s = ""

        # tail comment if the type is before the record
        if idf_style.tail_type == "before":
            if json_data["tail_comment"] != "":
                s += "\n"
                for line in json_data["tail_comment"].strip().split("\n"):
                    s += idf_style.get_tail_record_comment(line)

        # head comment
        if json_data["head_comment"] != "":
            comment = " " * spaces_nb + idf_style.get_record_comment(
                json_data["head_comment"],
                line_jump=False
            )
        else:
            comment = ""
        s += content + comment + "\n"

        # fields
        fields_nb = self._get_fields_nb()
        for i in range(fields_nb):
            # value
            tab = " " * idf_style.tab_len
            raw_value = json_data["data"].get(i, "")
            content = f"{tab}{raw_value}{';' if i == fields_nb-1 else ','}"
            spaces_nb = idf_style.comment_column_start - len(content)
            if spaces_nb < 0:
                spaces_nb = idf_style.tab_len
               
            # comment 
            raw_comment = json_data["comments"].get(i, "")
            if raw_comment != "":
                comment = " " * spaces_nb + idf_style.get_record_comment(
                    raw_comment,
                    line_jump=False
                )
            else:
                comment = ""
            s += content + comment + "\n"

        # tail comment if the type is after the record
        if idf_style.tail_type == "after":
            if json_data["tail_comment"] != "":
                s += "\n"
                for line in json_data["tail_comment"].strip().split("\n"):
                    s += idf_style.get_tail_record_comment(line)

        return s
