from .record import Record
from .queryset import Queryset
from .exceptions import FieldValidationError


def get_documented_add(self, record_descriptors):
    """
    this hack is used to document add function
    a methods __doc__ attribute is read-only (or must use metaclasses, what I certainly don't want to do...)
    we therefore create a function (who's __doc__ attribute is read/write), and will bind it to Table in __init__
    """
    def add(data=None, **or_data):
        return self.batch_add([or_data if data is None else data])[0]

    add.__doc__ = "\n".join([fd.ref.lower() for fd in record_descriptors if fd.ref is not None])

    return add


class Table:
    def __init__(self, table_descriptor, epm):
        self._dev_descriptor = table_descriptor
        self._epm = epm
        self._records = dict()

        # auto pk if first field is not a reference
        self._dev_auto_pk = table_descriptor.field_descriptors[0].detailed_type != "reference"

        # monkey-patch add
        self.add = get_documented_add(self, self._dev_descriptor.field_descriptors)

        # register table hooks
        table_hooks_references = self._dev_descriptor.field_descriptors[0].tags.get("reference-class-name")
        if table_hooks_references is not None:
            self._epm._dev_relations_manager.register_table_hook(table_hooks_references, self)
        
    def _dev_record_pk_was_updated(self, old_pk):
        # remove old pk
        record = self._records.pop(old_pk)

        # check uniqueness
        new_pk = record.get_pk()
        if new_pk in self._records:
            field_descriptor = record.get_field_descriptor(0)
            raise FieldValidationError(
                f"Primary key already exists, can't create. {field_descriptor.get_error_location_message(new_pk)}")

        # store with new pk
        self._records[new_pk] = record

    def _dev_add_inert(self, records_data):
        """
        inert: hooks and links are not activated
        """
        added_records = []
        for r_data in records_data:
            # create record
            record = Record(
                self,
                data=r_data
            )

            # store
            self._records[record.get_pk()] = record
            
            # remember record
            added_records.append(record)
        
        return added_records

    def _dev_remove_record_without_unregistering(self, record):
        del self._records[record.get_pk()]

    # --------------------------------------------- public api ---------------------------------------------------------
    def __repr__(self):
        return f"<Table {self.get_name()}>"

    def __str__(self):
        header = f"Table {self.get_name()} ({self.get_ref()})"
        if self._dev_auto_pk:
            return header
        return header + "\n" + "\n".join(f"  {pk}" for pk in sorted(self._records))

    def __getitem__(self, item):
        if self._dev_auto_pk:
            raise KeyError(f"table {self.get_ref()} does not have a primary key, can't use getitem syntax")
        try:
            return self._records[item]
        except KeyError:
            raise KeyError(f"table {self.get_ref()} does not contain a record who's pk is '{item}'")
    
    def __iter__(self):
        return iter(self._records.values())
    
    def __len__(self):
        return len(self._records)
    
    def get_ref(self):
        return self._dev_descriptor.table_ref
    
    def get_name(self):
        return self._dev_descriptor.table_name

    def get_epm(self):
        return self._epm

    def get_info(self):
        return self._dev_descriptor.get_info()
    
    # def add(self, data=None, **or_data):
    #     return self.batch_add([or_data if data is None else data])[0]
    # monkey-patched
    
    def batch_add(self, records_data):
        # add inert
        added_records = self._dev_add_inert(records_data)
        
        # activate hooks
        for r in added_records:
            r._dev_activate_hooks()

        # activate links
        for r in added_records:
            r._dev_activate_links()

        return added_records

    def select(self, filter_by=None):
        records = self._records.values() if filter_by is None else filter(filter_by, self._records.values())
        return Queryset(self, records=records)
    
    def one(self, filter_by=None):
        return Queryset(self, records=self._records.values()).one(filter_by=filter_by)

    # ------------------------------------------- export ---------------------------------------------------------------
    def to_json_data(self):
        return self.select().to_json_data()


    # todo: uniformize with queryset
