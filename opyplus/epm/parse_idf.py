from ..util import get_multi_line_copyright_message
from ..idd.util import table_name_to_ref


def parse_idf(file_like):
    """
    Records are created from string.
    They are not attached to idf yet.
    in idf: header comment, chapter comments, records
    in record: head comment, field comments, tail comment
    """
    # todo-later: manage record comments
    tables_data = {}
    head_comment = ""
    record_data = None
    make_new_record = True

    copyright_list = get_multi_line_copyright_message().split("\n")

    for i, raw_line in enumerate(file_like):
        # manage if copyright
        try:
            copyright_line = copyright_list[i]
            if raw_line.strip() == copyright_line:
                # skip copyright line
                continue
        except IndexError:
            pass

        # GET LINE CONTENT AND COMMENT
        split_line = raw_line.split("!")

        # no "!" in the raw_line
        if len(split_line) == 1:
            # this is an empty line
            if len(split_line[0].strip()) == 0:
                content, comment = None, None
            # this is a record line with no comments
            else:
                content, comment = split_line[0].strip(), None
        # there is at least one "!" in the raw_line
        else:
            # this is a comment line
            if len(split_line[0].strip()) == 0:
                content, comment = None, "!".join(split_line[1:])
            # this is a record line with a comment
            else:
                content, comment = split_line[0].strip(), "!".join(split_line[1:])

        # SKIP CURRENT LINE IF VOID
        if (content, comment) == (None, None):
            continue

        # NO CONTENT
        if not content:
            if record_data is None:  # we only manage head idf comment
                head_comment += comment.strip() + "\n"
            continue

        # CONTENT
        # check if record end and prepare
        record_end = content[-1] == ";"
        content = content[:-1]  # we tear comma or semi-colon
        content_l = [text.strip() for text in content.split(",")]

        # record creation if needed
        if make_new_record:
            # get table ref
            table_ref = table_name_to_ref(content_l[0].strip())

            # skip if special table
            if table_ref.lower() in (
                    "lead input",
                    "end lead input",
                    "simulation data",
                    "end simulation data"
            ):
                continue

            # declare table if necessary
            if table_ref not in tables_data:
                tables_data[table_ref] = []

            # create and store record
            record_data = dict()
            tables_data[table_ref].append(record_data)

            # prepare in case fields on the same line
            content_l = content_l[1:]
            make_new_record = False

        # fields
        for value_s in content_l:
            field_index = len(record_data)
            record_data[field_index] = value_s

        # signal that new record must be created
        if record_end:
            make_new_record = True

    # add comment key
    tables_data["_comment"] = head_comment
    return tables_data
