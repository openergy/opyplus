import uuid
import os
import collections
import textwrap

from .link import Link, NONE_LINK
from .record_hook import RecordHook, NONE_RECORD_HOOK
from .external_file import ExternalFile, NONE_EXTERNAL_FILE, get_external_files_dir_name
from ..exceptions import FieldValidationError


TAB_LEN = 4
COMMENT_COLUMN_START = 35


def get_type_level(value):
    if value is None:  # lowest type
        return 0

    if isinstance(value, str):
        return 1

    if isinstance(value, (int, float)):  # highest type
        return 2

    raise AssertionError(f"type not managed: {type(value)} ({value})")


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

        # comment
        self._comment = ""

        # signal initialized
        self._initialized = True

        # set data if any
        if data is not None:
            self._comment = data.pop("_comment", "")
            self._update_inert(data)

    def _field_key_to_index(self, ref_or_index):
        if isinstance(ref_or_index, int):
            if ref_or_index < 0:
                ref_or_index += len(self)
            if ref_or_index < 0:
                raise IndexError("index out of range")
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
        for i in range(len(self)):
            if i in self._data:
                continue

            # see if required field
            field_descriptor = self.get_field_descriptor(i)
            field_descriptor.check_not_required()

            # check not pk (in case idd was badly written)
            if i == 0 and not self._table._dev_no_pk:
                raise FieldValidationError(
                    f"Field is required (it is a pk). {field_descriptor.get_error_location_message()}")

    def _update_value_inert(self, index, value):
        """
        is only called by _update_inert
        """
        # get field descriptor
        field_descriptor = self._table._dev_descriptor.get_field_descriptor(index)

        # prepare value
        value = field_descriptor.deserialize(value, index, check_length=self.get_epm()._dev_check_length)

        # if relevant, store current id to signal change to table later on
        old_id = None
        if index == 0 and not self._table._dev_no_pk:
            # retrieve old value
            old_value = self._data.get(0)  # we use get, because record may not have an id yet if it is being created

            # manage record hooks (should not be any other special field)
            old_id = old_value.target_value if isinstance(old_value, RecordHook) else old_value

        # manage links
        if isinstance(value, Link):
            # de-activate current link if any
            current_link = self._data.get(index)
            if current_link is not None:
                current_link.unregister()

        # manage hooks
        if isinstance(value, RecordHook):
            current_record_hook = self._data.get(index)
            if current_record_hook is not None:
                # unregister or update
                if value is None:
                    current_record_hook.unregister()
                else:
                    # store old target value to signal table
                    current_record_hook.update(value)

        # manage external files
        if isinstance(value, ExternalFile):
            # unregister current external file if any
            current_external_file = self._data.get(index)
            if current_external_file is not None:
                current_external_file._dev_unregister()

        # if None remove and leave
        if value in (None, NONE_RECORD_HOOK, NONE_LINK, NONE_EXTERNAL_FILE):
            # we don't check required, because this method is called by _update_inert which does the job
            self._dev_set_none_without_unregistering(index, check_not_required=False)
            return

        # set value
        self._data[index] = value

        # signal id update if relevant
        if old_id is not None:
            self._table._dev_record_id_was_updated(old_id)

    def _dev_set_none_without_unregistering(self, index, check_not_required=True):
        # get field descriptor
        field_descriptor = self._table._dev_descriptor.get_field_descriptor(index)

        # check not required (if asked and check required mode)
        if check_not_required and self._table.get_epm()._dev_check_required:
            field_descriptor.check_not_required()

        # check not pk (in case idd was badly written)
        if not self._table._dev_no_pk and index == 0:
            raise FieldValidationError(
                f"Field is required (it is a pk). {field_descriptor.get_error_location_message()}")

        # set none
        if index in self._data:
            del self._data[index]

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
            raise TypeError("Can't use pop or insert for non extensible fields.")
        if cycle_len != 1:
            raise TypeError("Can only use pop or insert for extensible fields who's cycle length is 1.")

        return index

    def _unregister_hooks(self):
        for v in self._data.values():
            if isinstance(v, RecordHook):
                v.unregister()

    def _unregister_links(self):
        for v in self._data.values():
            if isinstance(v, Link):
                v.unregister()

    def _unregister_external_files(self):
        for v in self._data.values():
            if isinstance(v, ExternalFile):
                v._dev_unregister()

    def _dev_activate_hooks(self):
        for v in self._data.values():
            if isinstance(v, RecordHook):
                v.activate(self)

    def _dev_activate_links(self):
        for v in self._data.values():
            if isinstance(v, Link):
                v.activate(self)

    def _dev_activate_external_files(self):
        for v in self._data.values():
            if isinstance(v, ExternalFile):
                v._dev_activate(self.get_epm()._dev_external_files_manager)

    # --------------------------------------------- public api ---------------------------------------------------------
    # python magic
    def __repr__(self):
        if self._table is None:
            return "<Record (deleted)>"

        if self._table._dev_no_pk:
            return f"<Record {self.get_table()._dev_descriptor.table_name}>"

        return f"<Record {self.get_table().get_name()} '{self.id}'>"

    def __str__(self):
        if self._table is None:
            return repr(self)

        return self.to_idf()

    def __getitem__(self, item):
        """
        Parameters
        ----------
        item: field lowercase name or index

        Returns
        -------
        Field value
        """
        # prepare item
        item = self._field_key_to_index(item)

        # check not out of range
        if item > len(self):
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
        """
        Parameters
        ----------
        key: field lowercase name or index
        value: value to set
        """
        self.update({key: value})

    def __getattr__(self, item):
        """
        Parameters
        ----------
        item: field name
        """
        index = self._table._dev_descriptor.get_field_index(item)
        return self[index]

    def __setattr__(self, name, value):
        """
        Parameters
        ----------
        name: field lowercase name
        value: value to set
        """
        if name in self.__dict__ or not self._initialized:
            super().__setattr__(name, value)
            return
        self.update({name: value})

    def __dir__(self):
        return [
            f"f{i}" if fd.ref is None else fd.ref for
            (i, fd) in enumerate(self._table._dev_descriptor.field_descriptors)
        ] + list(self.__dict__)

    def __len__(self):
        biggest_index = -1 if (len(self._data) == 0) else max(self._data)

        # manage extensible
        if self.is_extensible():
            # go to end of extensible group
            cycle_start, cycle_len, patterns = self.get_extensible_info()
            extensible_position = biggest_index - cycle_start
            last_position = (extensible_position//cycle_len+1)*cycle_len-1
            biggest_index = cycle_start + last_position

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
            self_value = self.get_serialized_value(i)
            other_value = other.get_serialized_value(i)

            # types
            self_type_level = get_type_level(self_value)
            other_type_level = get_type_level(other_value)

            # different types
            if self_type_level < other_type_level:
                return True
            if self_type_level > other_type_level:
                return False

            # None, None
            if self_value is None:
                return False

            # different values
            if self_value < other_value:
                return True
            if self_value > other_value:
                return False

        # equality on common fields, len will settle
        return self_len <= other_len

    @property
    def id(self):
        """
        Returns
        -------
        If record has a name, returns its name, else returns record's python id.
        """
        return id(self) if self._table._dev_no_pk else self[0]

    # get context
    def get_epm(self):
        return self._table.get_epm()

    def get_table(self):
        return self._table

    def get_table_ref(self):
        return self._table.get_ref()

    # explore specific info
    def get_comment(self):
        return self._comment

    def get_serialized_value(self, ref_or_index, model_name=None):
        """
        Parameters
        ----------
        ref_or_index
        external_files_mode: str, default 'path'
            'path', 'pointer'
        model_file_path: str, default None
            if external files are asked in a relative fashion, relative path will be calculated relatively to
            model_file_path if given, else current directory

        Returns
        -------
        serialized value (only basic types: string, int, float, None, ...)
        """
        index = (
            self._table._dev_descriptor.get_field_index(ref_or_index) if isinstance(ref_or_index, str)
            else ref_or_index
        )

        # get value
        value = self._data.get(index)

        # serialize
        value = value.serialize() if isinstance(value, (Link, RecordHook)) else value

        # manage file names
        if isinstance(value, ExternalFile):
            value = os.path.join(get_external_files_dir_name(model_name=model_name), value.naive_short_ref)

        return value

    def get_pointed_records(self):
        """
        Returns
        -------
        MultiTableQueryset of all records pointing on record.
        """
        return self.get_epm()._dev_relations_manager.get_pointed_from(self)

    def get_pointing_records(self):
        """
        Returns
        -------
        MultiTableQueryset of all records pointed by record.
        """
        return self.get_epm()._dev_relations_manager.get_pointing_on(self)

    def get_external_files(self):
        """
        Returns
        -------
        List of ExternalFiles instances contained by record.
        """
        return [v for v in self._data.values() if isinstance(v, ExternalFile)]

    # construct
    def update(self, data=None, **or_data):
        """
        Updates simultaneously all given fields.

        Parameters
        ----------
        data: dictionary containing field lowercase names or index as keys, and field values as values (dict syntax)
        or_data: keyword arguments containing field names as keys (kwargs syntax)
        """

        # workflow
        # --------
        # (methods belonging to create/update/delete framework:
        #     epm._dev_populate_from_json_data, table.batch_add, record.update, queryset.delete, record.delete)
        # 1. add inert
        #     * data is checked
        #     * old links are unregistered
        #     * record is stored in table (=> id uniqueness is checked)
        # 2. activate: hooks, links, external files

        data = or_data if data is None else data

        self._update_inert(data)

        self._dev_activate_hooks()
        self._dev_activate_links()
        self._dev_activate_external_files()

    def set_comment(self, comment):
        # todo-later: manage properly (for the moment only used in to_idf)
        self._comment = comment

    def copy(self, new_name=None):
        """
        Parameters
        ----------
        new_name: str, default None
            record's new name (if table has a name). If None although record has a name, a random uuid will be given.

        Returns
        -------
        Copied record.
        """
        # todo: [GL] check this really works, !! must not use same link, hook, external_file, ... for different records
        # no pk tables can just be copied
        if self._table._dev_no_pk:
            return self._table.add(self._data)

        # for ref pk tables, must manage name
        name = str(uuid.uuid4()) if new_name is None else new_name
        new_data = dict((k, name if k == 0 else v) for (k, v) in self._data.items())
        return self._table.add(new_data)

    def set_defaults(self):
        """
        sets all empty fields for which a default value is defined to default value
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
        """
        This method only works for extensible fields. It allows to add values without precising their fields' names
        or indexes.

        Parameters
        ----------
        args: field values
        """
        if not self.is_extensible():
            raise TypeError("Can't use add_fields on a non extensible record.")

        # prepare update data
        self_len = len(self)
        data = dict([(self_len + i, args[i]) for i in range(len(args))])

        # update
        self.update(data)

    def pop(self, index=None):
        """
        This method only works for extensible fields. It allows to remove a value and shift all other values to fill
        the gap.

        Parameters
        ----------
        index: int, default None
            index of field to remove.

        Returns
        -------
        serialize value of popped field
        """
        # prepare index (will check for extensible)
        index = self._prepare_pop_insert_index(index=index)

        # get extensible info
        cycle_start, cycle_len, patterns = self.get_extensible_info()

        # remove extensible fields
        fields = self.clear_extensible_fields()

        # pop
        serialized_value = fields.pop(index-cycle_start)

        # add remaining
        self.add_fields(*fields)

        return serialized_value

    def insert(self, index, value):
        """
        This method only works for extensible fields. It allows to insert a value, and shifts all other following
        values.

        Parameters
        ----------
        index: position of insertion
        value: value to insert
        """
        # prepare index (will check for extensible)
        index = self._prepare_pop_insert_index(index=index)

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
        list of cleared fields (serialized)
        """
        if not self.is_extensible():
            raise TypeError("Can't use add_fields on a non extensible record.")
        cycle_start, cycle_len, patterns = self.get_extensible_info()
        return [self.get_serialized_value(i) for i in range(cycle_start, len(self))]

    # delete
    def delete(self):
        """
        Deletes record, and removes it from database.
        """
        # workflow
        # --------
        # (methods belonging to create/update/delete framework:
        #     epm._dev_populate_from_json_data, table.batch_add, record.update, queryset.delete, record.delete)
        # 1. unregister: links, hooks and external files
        # 3. remove from table without unregistering

        # unregister links
        self._unregister_links()

        # unregister hooks
        self._unregister_hooks()

        # unregister external files
        self._unregister_external_files()

        # tell table to remove without unregistering
        self.get_table()._dev_remove_record_without_unregistering(self)

        # make stale
        self._table = None
        self._data = None

    # get idd info
    def get_field_descriptor(self, ref_or_index):
        """
        Parameters
        ----------
        ref_or_index: str or int
            field lowercase name, or field position

        Returns
        -------
        Field descriptor (info contained in Idd)
        """
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

    def to_json_data(self, model_name=None):
        """
        Parameters
        ----------
        model_name: str, default None
            if given, will be used as external file directory base name

        Returns
        -------
        A dictionary of serialized data.
        """
        return collections.OrderedDict(
            [("_comment", self._comment)]
            + [(k, self.get_serialized_value(k, model_name=model_name)) for k in self._data]
        )

    def to_idf(self, model_name=None):
        """
        Parameters
        ----------
         model_name: str, default None
            if given, will be used as external file directory base name

        Returns
        -------
        idf string
        """
        json_data = self.to_json_data(model_name=model_name)

        # comment
        s = "" if self._comment == "" else f"{textwrap.indent(self._comment, '! ')}\n"

        # record descriptor ref
        s += f"{self._table._dev_descriptor.table_name},\n"

        # fields
        # fields_nb: we don't use len(self) but max(self). We wan't to stop if no more values (even base fields)
        #   because some idd records are defined without extensibles (although they should used them), for example
        #   construction, and eplus does not know what to do...
        fields_nb = max(self._data)+1
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
