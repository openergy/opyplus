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

            if td.extensible_info is None or i<td.extensible_info[0]:
                if "field" not in fd.tags:
                    print(i, table_ref)

