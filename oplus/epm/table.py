from .record import Record
from .queryset import Queryset


class Table:
    def __init__(self, table_descriptor, epm):
        self._dev_descriptor = table_descriptor
        self._epm = epm
        self._records = dict()

        # auto pk if first field is not a reference
        self._dev_auto_pk = "reference" not in table_descriptor.field_descriptors[0].tags

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

    # --------------------------------------------- public api ---------------------------------------------------------
    def __repr__(self):
        return f"<table: {self.get_ref()}>"
    
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
    
    def add(self, **record_data):
        return self.batch_add([record_data])[0]
    
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
    
    def remove(self, record):
        # todo: code
        pass
    
    def batch_remove(self, records):
        # todo: code
        pass
    
    def select(self, filter_by=None):
        records = self._records.values() if filter_by is None else filter(filter_by, self._records.values())
        return Queryset(self, records=records)
    
    def one(self, filter_by=None):
        return Queryset(self, records=self._records.values()).one(filter_by=filter_by)

    # ------------------------------------------- export ---------------------------------------------------------------
    def to_json_data(self, style=None):
        return self.select().to_json_data(style=style)

    def to_json(self, buffer_or_path=None, indent=2, style=None):
        return self.select().to_json(
            buffer_or_path=buffer_or_path,
            indent=indent,
            style=style
        )
