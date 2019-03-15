from oplus.epm.idd import Idd

if __name__ == "__main__":
    idd = Idd()
    for table_ref, td in idd.table_descriptors.items():
        for i, fd in enumerate(td.field_descriptors):
            if i == 0:
                continue
            if "reference-class-name" in fd.tags:
                print(table_ref)

            if "reference" in fd.tags:
                print(table_ref, i)

