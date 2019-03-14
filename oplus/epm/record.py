import uuid
import collections

from .link import Link
from .hook import Hook
from .exceptions import FieldValidationError

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
        """
        self._table = table  # when record is deleted, __init__ fields are set to None
        self._data = {}

        if data is not None:
            self._update_inert(data)

        # check that no required fields are missing
        for i in range(len(self)):
            if i in self._data:
                continue
            self._table._dev_descriptor.field_descriptors[i].check_not_required()

    def _field_key_to_index(self, ref_or_index):
        if isinstance(ref_or_index, int):
            return ref_or_index
        return self._table._dev_descriptor.get_field_index(ref_or_index)

    def _update_inert(self, data):
        # transform keys to indexes
        data = dict([(self._field_key_to_index(k), v) for (k, v) in data.items()])

        # set values inert (must be ordered, otherwise some extensible values may be rejected by mistake)
        for k, v in sorted(data.items()):
            self._dev_set_value_without_activating(k, v)

    def _dev_set_none_without_unregistering(self, index):
        if index not in self._data:
            return

        # get field descriptor
        field_descriptor = self._table._dev_descriptor.get_field_descriptor(index)

        # check not required
        field_descriptor.check_not_required()

        # remove
        del self._data[index]

    def _dev_set_value_without_activating(self, index, value):
        # get field descriptor
        field_descriptor = self._table._dev_descriptor.get_field_descriptor(index)
        
        # prepare value
        value = field_descriptor.deserialize(value)

        # manage if link
        if isinstance(value, Link):
            # de-activate current link if any
            current_link = self._data.get(index)
            if current_link is not None:
                current_link.unregister()
                
        # manage if hook
        if isinstance(value, Hook):
            current_hook = self._data.get(index)
            if current_hook is not None:
                current_hook.unregister()

        # if extensible: make appropriate checks
        if self.is_extensible():
            cycle_start, cycle_len, patterns = self.get_extensible_info()

            # see if extensible fields
            if index >= cycle_start:
                # 1. can't set to None if not last field
                if (value is None) and index != (len(self)-1):
                    raise FieldValidationError(
                        f"Can't set an extensible field to None, use pop or clear_extensible_fields. "
                        f"{field_descriptor.get_error_location_message()}"
                    )
                # 2. previous field must not be empty (except for first extensible field)
                if (index-1 >= cycle_start) and self._data.get(index-1) is None:
                    raise FieldValidationError(
                        f"Can't set an extensible field if some previous extensible fields are empty. "
                        f"{field_descriptor.get_error_location_message(value)}"
                    )
                
        # if None remove
        if value is None:
            self._dev_set_none_without_unregistering(index)

        # if relevant, store current pk to signal table
        old_pk = None
        if index == 0 and not self._table._dev_auto_pk:
            old_pk = self._data.get(0)  # we use get, because record may not have a pk yet if it is being created
        
        # else remove
        self._data[index] = value

        # signal pk update if relevant
        if old_pk is not None:
            self._table._dev_record_pk_was_updated(old_pk)

    def _prepare_pop_insert_index(self, index=None):
        if not self.is_extensible():
            raise TypeError("Can't use add_fields on a non extensible record.")

        # manage None or negative index
        self_len = len(self)
        if index is None:
            index = self_len - 1
        elif index < 0:
            index = self_len + index

        # check index is >= cycle_start
        cycle_start, cycle_len, patterns = self.get_extensible_info()
        if not cycle_start <= index < self_len:
            raise TypeError("Can't use pop for non extensible fields.")

        return index

    def _unregister_hooks(self):
        for v in self._data.values():
            if not isinstance(v, Hook):
                continue
            v.unregister()

    def _unregister_links(self):
        for v in self._data.values():
            if not isinstance(v, Link):
                continue
            v.unregister()

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

    # --------------------------------------------- public api ---------------------------------------------------------
    # python magic
    def __getitem__(self, item):
        if item >= len(self):
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
        self.update({key: value})

    def __getattr__(self, item):
        index = self._table._dev_descriptor.get_field_index(item)
        return self[index]

    def __setattr__(self, name, value):
        try:
            super().__setattr__(name, value)
            return
        except AttributeError:
            pass

        self.update({name: value})
        
    def __repr__(self):
        return f"<Deleted record>" if self._table is None else f"<{self.get_table_ref()}: {self.get_pk()}>"

    def __len__(self):
        biggest_index = -1 if (len(self._data) == 0) else max(self._data)
        return max(
            biggest_index+1,
            self._table._dev_descriptor.base_fields_nb
        )
    
    def __lt__(self, other):
        # compare tables
        self_ref = self.get_table_ref()
        other_ref = other.get_table_ref()
        if self_ref < other_ref:
            return True
        if self_ref > other_ref:
            return False
        
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

    # get info
    def get_raw_value(self, ref_or_index):
        index = (
            self._table._dev_descriptor.get_field_index(ref_or_index) if isinstance(ref_or_index, str)
            else ref_or_index
        )
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

    def get_field_descriptor(self, ref_or_index):
        if isinstance(ref_or_index, int):
            index = ref_or_index
        else:
            index = self._table._dev_descriptor.get_field_index(ref_or_index)
        return self._table._dev_descriptor.get_field_descriptor(index)
    
    def get_pointed_records(self):
        return self.get_epm()._dev_relations_manager.get_pointed_from(self)
    
    def get_pointing_records(self):
        return self.get_epm()._dev_relations_manager.get_pointing_on(self)

    def is_extensible(self):
        return self.get_extensible_info() is not None
    
    def get_extensible_info(self):
        """
        Returns
        -------
        cycle_start, cycle_len, patterns
        """
        return self._table._dev_descriptor.extensible_info

    # construct
    def update(self, _record_data=None, **record_data):
        self._update_inert(record_data if _record_data is None else record_data)
        self._dev_activate_hooks()
        self._dev_activate_links()

    def copy(self):
        # create new record
        new_data = dict([(
            str(uuid.uuid4()) if self._table._dev_descriptor.get_field_descriptor(i).detailed_type == "reference"
            else self._data[i]
        ) for i in self._data
        ])
        return self._table.add(new_data)

    # construct extensible fields
    def add_fields(self, *args):
        if not self.is_extensible():
            raise TypeError("Can't use add_fields on a non extensible record.")

        # prepare update data
        self_len = len(self)
        data = dict([(self_len + i, args[i]) for i in range(len(args))])

        # update
        self._update(data)

    def pop(self, index=None):
        # prepare index (will check for extensible)
        index = self._prepare_pop_insert_index(index=index)

        # get extensible info
        cycle_start, cycle_len, patterns = self.get_extensible_info()
        
        # remove extensible fields
        fields = self.clear_extensible_fields()
        
        # pop
        fields.pop(cycle_start-index)
        
        # add remaining
        self.add_fields(*fields)

    def insert(self, index, value):
        # prepare index (will check for extensible)
        index = self._prepare_pop_insert_index(index=index)

        # get extensible info
        cycle_start, cycle_len, patterns = self.get_extensible_info()

        # remove extensible fields
        fields = self.clear_extensible_fields()

        # insert
        fields.insert(index, value)

        # add new list
        self.add_fields(*fields)

    def clear_extensible_fields(self):
        """
        Returns
        -------
        list of cleared fields
        """
        if not self.is_extensible():
            raise TypeError("Can't use add_fields on a non extensible record.")
        cycle_start, cycle_len, patterns = self.get_extensible_info()
        return [self._data.pop(i) for i in range(cycle_start, len(self))]

    # delete
    def delete(self):
        # unregister links
        self._unregister_links()

        # unregister hooks
        self._unregister_hooks()

        # tell table to remove without unregistering
        self.get_table()._dev_remove_record_without_unregistering(self)

        # make stale
        self._table = None
        self._data = None
        
    # --------------------------------------------- export -------------------------------------------------------------
    def to_dict(self):
        return collections.OrderedDict(sorted(self._data.items()))
    
    def to_json_data(self):
        return collections.OrderedDict([(k, self.get_raw_value(k)) for k in self._data])
    
    def to_idf(self):
        json_data = self.to_json_data()
            
        # record descriptor ref
        s = f"{self._table._dev_descriptor.table_name},\n"

        # fields
        fields_nb = len(self)
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

    # todo: get_info and str