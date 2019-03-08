from ..configuration import CONF
from .style import style_library, IdfStyle
from .util import table_name_to_ref


def parse_idf(file_like, style=None):
    """
    Records are created from string. They are not attached to idf yet.
    in idf: header comment, chapter comments, records
    in record: head comment, field comments, tail comment
    """
    if style is None:
        style = style_library[CONF.default_read_style]
    if isinstance(style, IdfStyle):
        style = style
    elif isinstance(style, str):
        if style in style_library.keys():
            style = style_library[style]
        else:
            style = style_library[CONF.default_read_style]
    else:
        style = style_library[CONF.default_read_style]

    tables_data, head_comment, tail_comment = {}, "", ""
    record_data = None
    make_new_record = True

    for i, raw_line in enumerate(file_like):
        # GET LINE CONTENT AND COMMENT
        split_line = raw_line.split("!")

        # No "!" in the raw_line
        if len(split_line) == 1:
            # This is an empty line
            if len(split_line[0].strip()) == 0:
                content, comment = None, None
            # This is a record line with no comments
            else:
                content, comment = split_line[0].strip(), None
        # There is at least one "!" in the raw_line
        else:
            # This is a comment line
            if len(split_line[0].strip()) == 0:
                content, comment = None, "!".join(split_line[1:])
            # This is a record line with a comment
            else:
                content, comment = split_line[0].strip(), "!".join(split_line[1:])

        # SKIP CURRENT LINE IF VOID
        if (content, comment) == (None, None):
            continue

        # NO CONTENT
        if not content:
            if record_data is None:  # head idf comment
                if style is None:
                    head_comment += comment.strip() + "\n"
                elif comment[:len(style.chapter_key)] == style.chapter_key:
                    continue
                elif comment[:len(style.head_key)] == style.head_key:
                    comment = comment[len(style.head_key):].strip()
                    head_comment += comment + "\n"
            else:
                if style is None:
                    continue
                elif comment[:len(style.chapter_key)] == style.chapter_key:
                    continue
                elif comment[:len(style.tail_record_key)] == style.tail_record_key:
                    comment = comment[len(style.tail_record_key):].strip().replace("\n", "")
                    if style.tail_type == "before":
                        tail_comment += comment + "\n"
                    elif style.tail_type == "after":
                        new_comment = comment.strip()
                        if new_comment != "":
                            old_comment = record_data["tail_comment"]
                            new_comment = (
                                f"{old_comment}{new_comment}\n" if old_comment != "" else f"{new_comment}\n"
                            )
                            record_data["tail_comment"] = new_comment

            continue

        # CONTENT
        # check if record end and prepare
        record_end = content[-1] == ";"
        content = content[:-1]  # we tear comma or semi-colon
        content_l = [text.strip() for text in content.split(",")]

        if comment:
            if style is None:
                comment = comment.strip().replace("\n", "")
            elif comment[:len(style.record_key)] == style.record_key:
                comment = comment[len(style.record_key):].strip().replace("\n", "")
            else:
                comment = ""

        field_comment = comment

        # record creation if needed
        if make_new_record:
            if not record_end and len(content_l) > 1:
                head_comment = ""
                field_comment = comment
            else:
                head_comment = comment
                field_comment = ""

            # get table
            table_ref = table_name_to_ref(content_l[0].strip())
            if table_ref not in tables_data:
                tables_data[table_ref] = []
            # table = getattr(self, table_ref)

            # create and store record
            record_data = dict(
                data=dict(),
                comments=dict(),
                head_comment=head_comment,
                tail_comment=""
            )
            tables_data[table_ref].append(record_data)

            # prepare in case fields on the same line
            content_l = content_l[1:]
            make_new_record = False

        # fields
        for value_s in content_l:
            field_index = len(record_data["data"])
            record_data["data"][field_index] = value_s
            if field_comment != "":
                record_data["comments"][field_index] = field_comment

        # signal that new record must be created
        if record_end:
            if style:
                if style.tail_type == "before":
                    record_data["tail_comment"] = tail_comment
                    tail_comment = ""
            make_new_record = True

    return tables_data
