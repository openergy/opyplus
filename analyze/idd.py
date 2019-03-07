from oplus.idd.idd import Idd

if __name__ == "__main__":
    idd = Idd()
    for table_ref, td in idd.table_descriptors.items():
        for i, fd in enumerate(td.field_descriptors):
            if fd.name is None:
                print(table_ref, i)
                break

