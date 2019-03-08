from .record import Record


class Table:
    def __init__(self, table_descriptor, idf):
        self._dev_descriptor = table_descriptor
        self._idf = idf
        self._records = dict()

        # auto pk if first field is not a reference
        self._dev_auto_pk = not table_descriptor.field_descriptors[0].has_tag("reference")

    def _dev_add_inert(self, records_data):
        """
        inert: hooks and links are not activated
        """
        added_records = []
        for r_data in records_data:
            # create record
            record = Record(
                self,
                data=r_data["data"],
                comments=r_data["comments"],
                head_comment=r_data["head_comment"],
                tail_comment=r_data["tail_comment"]
            )

            # store
            self._records[record.get_pk()] = record
            
            # remember record
            added_records.append(record)
        
        return added_records

    # --------------------------------------------- public api ---------------------------------------------------------
    def get_ref(self):
        return self._dev_descriptor.table_ref

    def get_idf(self):
        return self._idf
