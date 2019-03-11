import uuid
import io
import collections

from ..configuration import CONF
from .exceptions import ObsoleteRecordError, IsPointedError, BrokenEpmError
from .multi_table_queryset import MultiTableQueryset
from .link import Link
from .hook import Hook

TAB_LEN = 4
COMMENT_COLUMN_START = 35


def get_type_level(value):
    if value is None:  # lowest type
        return 0

    if isinstance(value, str):
        return 1

    if isinstance(value, (int, float)):  # highest type
        return 2


class Record:
    def __init__(self, table, data=None):
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
        # todo: manage what happens if comment on field > fields_nb (extensible), but no data.
        self._table = table
        self._data = {}

        if data is not None:
            for k, v in data.items():
                self._dev_set_value_inert(k, v)

        # check required
        for i, fd in enumerate(self._table._dev_descriptor.field_descriptors):
            if ("required-field" in fd.tags) and (i not in self._data):
                raise RuntimeError("field is required")  # todo: manage errors properly
        
        # todo: manage comments properly

    def _dev_set_value_inert(self, field_index_or_ref, value):
        """
        inert: links and hooks will not be activated
        """
        # get index
        if isinstance(field_index_or_ref, int):
            index = field_index_or_ref
        else:
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
        if value is None and index in self._data:
            if "required-field" in field_descriptor.tags:
                raise RuntimeError("field is required, can't be none")  # todo: manage errors properly
            
            # remove
            del self._data[index]
        
        # else remove
        else:
            self._data[index] = value
            
    def _dev_activate_hooks(self):
        for v in self._data.values():
            if not isinstance(v, Hook):
                continue
            v.activate(self)

    def _dev_activate_links(self):
        for v in self._data.values():
            if not isinstance(v, Link):
                continue
            v.activate(self)
    
    def _get_fields_nb(self):
        return max(max(self._data.keys())+1, self._table._dev_descriptor.base_fields_nb)

    # --------------------------------------------- public api ---------------------------------------------------------
    def __getitem__(self, item):
        if item >= self._get_fields_nb():
            raise IndexError("index out of range")

        # get value
        value = self._data.get(item)

        # transform if hook or link
        if isinstance(value, Hook):
            return value.value
        if isinstance(value, Link):
            return value.target_record

        # return otherwise
        return value

    def __setitem__(self, key, value):
        pass
        # todo: don't forget to notify pk update

    def __getattr__(self, item):
        index = self._table._dev_descriptor.get_field_index(item)
        return self[index]

    def __setattr__(self, name, value):
        try:
            super().__setattr__(name, value)
            return
        except AttributeError:
            pass

        # todo: code
        # todo: don't forget to notify pk update
        
    def __repr__(self):
        # todo: manage obsolete
        return f"<{self.get_table_ref()}: {self.get_pk()}>"

    def __len__(self):
        return len(self._data)
    
    def __lt__(self, other):
        # get lengths
        self_len = len(self)
        other_len = len(other)
        common_length = min(self_len, other_len)

        # compare field by field
        for i in range(common_length):
            # values
            self_value = self.get_raw_value(i)
            other_value = self.get_raw_value(other)

            # types
            self_type_level = get_type_level(self_value)
            other_type_level = get_type_level(other_value)

            # different types
            if self_type_level < other_type_level:
                return True
            if self_type_level > other_type_level:
                return False

            # different values
            if self_value < other_value:
                return True
            if self_value > other_value:
                return False

        # equality on common fields, len will settle
        return self_len <= other_len

    def get_raw_value(self, ref_or_index):
        index = (self._table._dev_descriptor.get_field_index(ref_or_index) if isinstance(ref_or_index, str)
                 else ref_or_index)
        value = self._data.get(index)
        return value.serialize() if isinstance(value, (Link, Hook)) else value
    
    def get_table_ref(self):
        return self._table.get_ref()

    def get_pk(self):
        """
        Returns
        -------
        python id if auto pk, else pk
        """
        return id(self) if self._table._dev_auto_pk else self[0]
    
    def get_epm(self):
        return self._table.get_epm()
    
    def get_table(self):
        return self._table
    
    def get_pointed_records(self):
        # todo: code
        pass
    
    def get_pointing_records(self):
        # todo: code
        pass
    
    def update(self, **data):
        # todo: code
        pass
        
    # --------------------------------------------- export -------------------------------------------------------------
    def to_dict(self):
        return collections.OrderedDict(sorted(self._data.items()))
    
    def to_json_data(self):
        return collections.OrderedDict([(k, self.get_raw_value(k)) for k in self._data])
    
    def to_idf(self):
        # todo: manage obsolescence ?
        #  self._check_obsolescence()
        json_data = self.to_json_data()
            
        # record descriptor ref
        s = f"{self._table._dev_descriptor.table_name},\n"

        # fields
        fields_nb = self._get_fields_nb()
        for i in range(fields_nb):
            # value
            tab = " " * TAB_LEN
            raw_value = json_data.get(i, "")
            content = f"{tab}{raw_value}{';' if i == fields_nb-1 else ','}"

            # comment
            spaces_nb = COMMENT_COLUMN_START - len(content)
            if spaces_nb < 0:
                spaces_nb = TAB_LEN
               
            # comment
            comment = " " * spaces_nb + f"! {self._table._dev_descriptor.get_field_descriptor(i).name}"

            # store
            s += f"{content}{comment}\n"

        return s
