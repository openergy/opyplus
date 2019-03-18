import uuid
import collections

from .link import Link
from .record_hook import RecordHook
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
    _initialized = False  # used by __setattr__

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

        # signal initialized
        self._initialized = True

        # set data if any
        if data is not None:
            self._update_inert(data)

    def _field_key_to_index(self, ref_or_index):
        if isinstance(ref_or_index, int):
            return ref_or_index
        return self._table._dev_descriptor.get_field_index(ref_or_index)

    def _update_inert(self, data):
        # transform keys to indexes
        data = dict([(self._field_key_to_index(k), v) for (k, v) in data.items()])

        # set values inert (must be ordered, otherwise some extensible values may be rejected by mistake)
        for k, v in sorted(data.items()):
            self._update_value_inert(k, v)

        # leave if empty required fields are tolerated
        # check that no required fields are missing
        if not self._table.get_epm()._dev_check_required:
            return

        # check required

        # prepare extensible checks
        is_extensible = self.is_extensible()
        if is_extensible:
            cycle_start, cycle_len, patterns = self.get_extensible_info()
        else:
            cycle_start, cycle_len, patterns = None, None, None

        # iter fields
        for i in range(len(self)):
            if i in self._data:
                continue

            # see if required field
            field_descriptor = self._table._dev_descriptor.field_descriptors[i]
            field_descriptor.check_not_required()

            # check not pk (in case idd was baddly written)
            if i == 0 and not self._table._dev_auto_pk:
                raise FieldValidationError(
                    f"Field is required (it is a pk). {field_descriptor.get_error_location_message()}")

            # if extensible: make appropriate checks
            if is_extensible and i >= cycle_start:
                value = self._data.get(i)
                if value is None:
                    raise FieldValidationError(
                        f"An extensible field can't be empty. Pop or clear_extensible_fields may be usefull. "
                        f"{field_descriptor.get_error_location_message()}"
                    )

    def _update_value_inert(self, index, value):
        """
        is only called by _update_inert
        """
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
        if isinstance(value, RecordHook):
            current_record_hook = self._data.get(index)
            if current_record_hook is not None:
                current_record_hook.unregister()

        # if None remove and leave
        if value is None:
            # we don't check required, because this method is called by _update_inert which does the job
            self._dev_set_none_without_unregistering(index, check_not_required=False)
            return

        # if relevant, store current pk to signal table
        old_pk = None
        if index == 0 and not self._table._dev_auto_pk:
            old_pk = self._data.get(0)  # we use get, because record may not have a pk yet if it is being created

        # set value
        self._data[index] = value

        # signal pk update if relevant
        if old_pk is not None:
            self._table._dev_record_pk_was_updated(old_pk)

    def _dev_set_none_without_unregistering(self, index, check_not_required=True):
        # get field descriptor
        field_descriptor = self._table._dev_descriptor.get_field_descriptor(index)

        # check not required (if asked and check required mode)
        if check_not_required and self._table.get_epm()._dev_check_required:
            field_descriptor.check_not_required()

        # check not pk (in case idd was badly written)
        if not self._table._dev_auto_pk and index == 0:
            raise FieldValidationError(
                f"Field is required (it is a pk). {field_descriptor.get_error_location_message()}")

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
            if not isinstance(v, RecordHook):
                continue
            v.unregister()

    def _unregister_links(self):
        for v in self._data.values():
            if not isinstance(v, Link):
                continue
            v.unregister()

    def _dev_activate_hooks(self):
        for v in self._data.values():
            if not isinstance(v, RecordHook):
                continue
            v.activate(self)

    def _dev_activate_links(self):
        for v in self._data.values():
            if not isinstance(v, Link):
                continue
            v.activate(self)

    # --------------------------------------------- public api ---------------------------------------------------------
    # python magic
    def __repr__(self):
        if self._table is None:
            return "<Record (deleted)>"

        if self._table._dev_auto_pk:
            return f"<Record {self.get_table()._dev_descriptor.table_name}>"

        return f"<Record {self.get_table().get_name()} '{self.get_pk()}'>"

    def __str__(self):
        if self._table is None:
            return repr(self)

        return self.to_idf()

    def __getitem__(self, item):
        if item >= len(self):
            raise IndexError("index out of range")

        # get value
        value = self._data.get(item)

        # transform if hook or link
        if isinstance(value, RecordHook):
            return value.target_value
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
        if self._initialized:
            self.update({name: value})
            return
        super().__setattr__(name, value)

    def __dir__(self):
        return [
            f"f{i}" if fd.ref is None else fd.ref for
            (i, fd) in enumerate(self._table._dev_descriptor.field_descriptors)
        ] + list(self.__dict__)

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

    # get context
    def get_epm(self):
        return self._table.get_epm()

    def get_table(self):
        return self._table

    def get_table_ref(self):
        return self._table.get_ref()

    # explore specific info
    def get_pk(self):
        """
        Returns
        -------
        python id if auto pk, else pk
        """
        return id(self) if self._table._dev_auto_pk else self[0]

    def get_raw_value(self, ref_or_index):
        index = (
            self._table._dev_descriptor.get_field_index(ref_or_index) if isinstance(ref_or_index, str)
            else ref_or_index
        )
        value = self._data.get(index)
        return value.serialize() if isinstance(value, (Link, RecordHook)) else value

    def get_pointed_records(self):
        return self.get_epm()._dev_relations_manager.get_pointed_from(self)

    def get_pointing_records(self):
        return self.get_epm()._dev_relations_manager.get_pointing_on(self)

    # construct
    def update(self, data=None, **or_data):
        data = or_data if data is None else data
        if len(data) == 0:
            return
        self._update_inert(data)
        self._dev_activate_hooks()
        self._dev_activate_links()

    def copy(self, new_name=None):
        # auto pk tables can just be copied
        if self._table._dev_auto_pk:
            return self._table.add(self._data)

        # for ref pk tables, must manage name
        name = str(uuid.uuid4()) if new_name is None else new_name
        new_data = dict((k, name if k == 0 else v) for (k, v) in self._data.items())
        return self._table.add(new_data)

    def set_defaults(self):
        """
        sets all empty fields with default value to default value
        """
        defaults = {}
        for i in range(len(self)):
            if i in self._data:
                continue
            default = self.get_field_descriptor(i).tags.get("default", [None])[0]
            if default is not None:
                defaults[i] = default

        self.update(defaults)

    # construct extensible fields
    def add_fields(self, *args):
        if not self.is_extensible():
            raise TypeError("Can't use add_fields on a non extensible record.")

        # prepare update data
        self_len = len(self)
        data = dict([(self_len + i, args[i]) for i in range(len(args))])

        # update
        self.update(data)

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

    # get idd info
    def get_field_descriptor(self, ref_or_index):
        if isinstance(ref_or_index, int):
            index = ref_or_index
        else:
            index = self._table._dev_descriptor.get_field_index(ref_or_index)
        return self._table._dev_descriptor.get_field_descriptor(index)

    def get_info(self):
        return self._table._dev_descriptor.get_info()

    def is_extensible(self):
        return self.get_extensible_info() is not None

    def get_extensible_info(self):
        """
        Returns
        -------
        cycle_start, cycle_len, patterns
        """
        return self._table._dev_descriptor.extensible_info
        
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
            name = self._table._dev_descriptor.get_extended_name(i)
            comment = "" if name is None else " " * spaces_nb + f"! {name}"

            # store
            s += f"{content}{comment}\n"

        return s
