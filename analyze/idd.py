from oplus.idf.idd import Idd

if __name__ == "__main__":
    idd = Idd()
    for table_ref, td in idd.table_descriptors.items():
        if len(td.field_descriptors) == 0:
            raise AttributeError("O")
        # for i, fd in enumerate(td.field_descriptors):
        #     if fd.name is None:
        #         print(table_ref, i)
        #         break

