import io
import itertools
from oplus import CONF  # todo: change conf style ?
from contextlib import contextmanager
from oplus.idd.idd import Idd
from .table import Table
from .queryset import Queryset
from .cache import CachedMixin, cached, clear_cache
from .record import Record
from .record_link_set import RecordLinkSet
from ..util import get_string_buffer
from .style import IdfStyle, style_library
from .exceptions import BrokenIdfError, IsPointedError
from ..idd.table_descriptor import table_name_to_ref


class Idf(CachedMixin):
    _dev_record_cls = Record  # for subclassing
    _dev_table_cls = Table  # for subclassing
    _dev_idd_cls = Idd  # for subclassing

    @classmethod
    def get_or_create_idf(cls, idf_or_path, encoding=None):
        """
        Arguments
        ---------
        idf_or_path: idf record or idf file path
        encoding

        Returns
        -------
        Idf record
        """
        if isinstance(idf_or_path, str):
            return cls(idf_or_path, encoding=encoding)
        elif isinstance(idf_or_path, cls):
            return idf_or_path
        raise ValueError(
            "'idf_or_path' must be a path or an Idf. Given object: '{idf_or_path}', type: '{type(idf_or_path)}'."
        )

    def __init__(self, path_or_content=None, idd_or_path=None, encoding=None, style=None):
        """
        Arguments
        ---------
        path_or_content: idf path, content str, content bts or file_like. If path, must end by .idf.
        idd_or_path: Idd record or idd path. If None, default will be chosen (most recent EPlus version installed on
            computer)
        encoding
        style
        """
        self._dev_activate_cache()

        self._encoding = CONF.encoding if encoding is None else encoding
        self._constructing_mode_counter = 0
        self._dev_idd = self._dev_idd_cls.get_idd(idd_or_path, encoding=encoding)
        self._tables = dict([  # {lower_ref: table, ...}
            (lower_ref, Table(rd, self))
            for lower_ref, rd in self._dev_idd.table_descriptors.items()
        ])

        # prepare record links
        self._record_links = RecordLinkSet()

        # # get string buffer and store path (for info)
        # buffer, path = get_string_buffer(path_or_content, "idf", self._encoding)
        # self._dev_path = path_or_content
        #
        # # raw parse and parse
        # with buffer as f:
        #     self._records, self._head_comments = self._dev_parse(f, style)

    # parse
    def _dev_parse(self, file_like, style=None):
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

        records, head_comments = [], ""
        record = None
        make_new_record = True

        tail_comments = ""

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
                if record is None:  # head idf comment
                    if style is None:
                        head_comments += comment.strip() + "\n"
                    elif comment[:len(style.chapter_key)] == style.chapter_key:
                        continue
                    elif comment[:len(style.head_key)] == style.head_key:
                        comment = comment[len(style.head_key):].strip()
                        head_comments += comment + "\n"
                else:
                    if style is None:
                        continue
                    elif comment[:len(style.chapter_key)] == style.chapter_key:
                        continue
                    elif comment[:len(style.tail_record_key)] == style.tail_record_key:
                        comment = comment[len(style.tail_record_key):].strip().replace("\n", "")
                        if style.tail_type == "before":
                            tail_comments += comment + "\n"
                        elif style.tail_type == "after":
                            new_comment = comment.strip()
                            if new_comment != "":
                                old_comment = record.get_tail_comment()
                                new_comment = (
                                    f"{old_comment}{new_comment}\n" if old_comment != "" else f"{new_comment}\n"
                                )
                                record.set_tail_comment(new_comment)

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
                    comment = None

            field_comment = comment

            # record creation if needed
            if make_new_record:
                if not record_end and len(content_l) > 1:
                    head_comment = None
                    field_comment = comment
                else:
                    head_comment = comment
                    field_comment = None

                # get table
                table_ref = table_name_to_ref(content_l[0].strip())
                table = getattr(self, table_ref)

                # create and store record
                record = self._dev_record_cls(table, head_comment=head_comment)
                records.append(record)

                # prepare in case fields on the same line
                content_l = content_l[1:]
                make_new_record = False

            # fields
            for value_s in content_l:
                record.add_field(value_s, comment=field_comment)

            # signal that new record must be created
            if record_end:
                if style:
                    if style.tail_type == "before":
                        record.set_tail_comment(tail_comments)
                        tail_comments = ""
                make_new_record = True

        return records, head_comments

    # links
    @cached
    def _dev_get_pointed_link(self, pointing_ref, pointing_index, pointing_raw_value):
        # get field descriptor
        fieldd = self._dev_idd.get_record_descriptor(pointing_ref).get_field_descriptor(pointing_index)

        # check if object-list
        assert fieldd.detailed_type == "object-list", \
            "Only 'object-list' fields can point on an object. " \
                f"Wrong field given. Ref: '{pointing_ref}', index: '{pointing_index}'."

        # check if a record is pointed
        if pointing_raw_value == "":  # no record pointed
            return None, None

        # iter through link possibilities and return if found
        link_names_l = fieldd.get_tag("object-list")
        for link_name in link_names_l:
            for rd, field_index in self._dev_idd.pointed_links(link_name):
                # tbl = self.get_table(rd.table_ref)
                for record in getattr(self, rd.table_ref):
                    # rv = record.get_raw_value(field_index)
                    if record.get_raw_value(field_index) == pointing_raw_value:
                        return record, field_index

        raise RuntimeError(
            f"Link not found. "
            f"Field 'object-list' tag values: {str(link_names_l)}, field value : '{pointing_raw_value}'"
        )

    @cached
    def _dev_get_pointing_links(self, pointed_ref, pointed_index, pointed_raw_value):
        # get field descriptor
        fieldd = self._dev_idd.get_record_descriptor(pointed_ref).get_field_descriptor(pointed_index)

        # check if reference
        assert fieldd.detailed_type == "reference", \
            "Only 'reference' fields can be pointed by an object. Wrong field given. " \
                f"Ref: '{pointed_ref}', index: '{pointed_index}'."

        # check if a record can be pointing
        if pointed_raw_value == "":
            return []

        # fetch links
        links_l = []
        for link_name in fieldd.get_tag("reference"):
            for record_descriptor, pointing_index in self._dev_idd.pointing_links(link_name):
                for record in getattr(self, record_descriptor.table_ref):
                    if pointing_index >= record._dev_fields_nb:
                        continue
                    if record.get_raw_value(pointing_index) == pointed_raw_value:
                        links_l.append([record, pointing_index])
        return links_l

    # checks
    def _check_new_reference(self, new_record_ref, new_record_index, reference):
        if reference == "":
            return None
        # check that there is no duplicate reference (i.e. none of the links which will point to this field already
        # points to another field with the same reference)
        links_l = self._dev_get_pointing_links(new_record_ref, new_record_index, reference)
        if len(links_l) != 0:
            raise BrokenIdfError(
                "New record has same reference at index '%s' as other record of same link name. "
                "Other record ref: '%s', index: '%s'. The value at that field must be changed." %
                (new_record_index, links_l[0][0].get_table_ref(), links_l[0][1])
            )

    def _check_duplicate_references(self):
        # we create a dict containing for each link_name a set of references to check that they are unique
        ref_d = dict()
        for record in self._records:
            # check reference uniqueness
            record_descriptor = self._dev_idd.get_record_descriptor(record.get_table_ref())
            for i in range(record._dev_fields_nb):
                fieldd = record_descriptor.get_field_descriptor(i)
                if fieldd.detailed_type == "reference":
                    reference = record.get_raw_value(i)
                    for link_name in fieldd.get_tag("reference"):
                        # for each link name add the reference to the set to check for uniqueness
                        if link_name not in ref_d:
                            ref_d[link_name] = set()
                        if reference in ref_d[link_name]:
                            raise BrokenIdfError(
                                "Reference duplicate for link name: {}\n".format(link_name) +
                                "Reference: {}\n".format(reference) +
                                "Detected while checking record ref: {}\n".format(record.get_table_ref()) +
                                "Field: {}".format(i)
                            )
                        ref_d[link_name].add(reference)

    # records
    @clear_cache
    def _dev_add_naive_record(self, naive_record, position=None):
        """
        checks references uniqueness

        Parameters
        ----------
        naive_record: record
            a record that has been created, but not inserted into idf
        position: int
        """
        # check reference uniqueness
        record_descriptor = self._dev_idd.get_record_descriptor(naive_record.get_table_ref())
        for i in range(naive_record._dev_fields_nb):
            fieldd = record_descriptor.get_field_descriptor(i)
            if fieldd.detailed_type == "reference" and self._constructing_mode_counter == 0:
                self._check_new_reference(record_descriptor.table_ref, i, naive_record.get_raw_value(i))

        # add record
        if position is None:
            self._records.append(naive_record)
        else:
            self._records.insert(position, naive_record)

        # return new record
        return naive_record

    @cached
    def _dev_select_from_table(self, table_ref):
        """
        purpose: this function is cached
        """
        table = getattr(self, table_ref)
        return Queryset(table, [r for r in self._records if r.get_table() is table])

    # --------------------------------------------- public api ---------------------------------------------------------
    # python magic
    def __dir__(self):
        return [t.get_ref() for t in self._tables.values()] + [k for k in self.__dict__ if k[0] != "_"]

    def __getattr__(self, item):
        try:
            return self._tables[item.lower()]
        except KeyError:
            raise AttributeError(f"No table with reference '{item}'.")

    def __iter__(self):
        return (k for (k, _) in itertools.groupby(self._records, key=lambda x: x.get_table()))

    def __len__(self):
        return len(self._records)

    def __repr__(self):
        building_records = self.building.select()
        building = None if len(building_records) == 0 else building_records[0]
        return "<Idf>" if building is None else f"<Idf: {building.name}>"

    def __str__(self):
        return repr(self)

    # get/set comments
    def get_comment(self):
        return self._head_comments

    @clear_cache
    def set_comment(self, value):
        self._head_comments = str(value).strip()

    # add records
    @clear_cache
    def add(self, table_ref, **record_data):
        """
        Parameters
        ----------
        table_ref
        record_data

        Returns
        -------
        created record
        """
        return self.batch_add({table_ref: [record_data]})[0]

    @clear_cache
    def batch_add(self, records_data):
        """
        Parameters
        ----------
        records_data: dict
            {table_ref: [list of records data], ...}

        Returns
        -------
        list of created records
        """
        # create records, using under construction
        created_records = []
        with self.is_under_construction():
            for table_ref, _records_data in records_data.items():
                for record_data in _records_data:
                    r = Record(getattr(self, table_ref))
                    for k, v in record_data.items():
                        setattr(r, k, v)
                    created_records.append(r)
        return created_records

    # add records
    @clear_cache
    def add_from_string(self, record_str, position=None):
        """
        Parameters
        ----------
        record_str: string describing the new record to add
        position: if None, will be added at the end, else will be added at asked position
            (using 'insert' python builtin function for lists)

        Returns
        -------
        added record
        """
        return self.batch_add_from_string([record_str], position=position)[0]

    @clear_cache
    def batch_add_from_string(self, records_str, position=None):
        """
        Adds new record to the idf, at required position.

        Arguments
        ---------
        records_str: list of strings describing the new records that will be added to idf
        position: if None, will be added at the end, else will be added at asked position
            (using 'insert' python builtin function for lists)

        Returns
        -------
        added records
        """
        # create records, using under construction
        created_records = []
        with self.is_under_construction():
            for new_str in records_str:
                records, comments_l = self._dev_parse(
                    io.StringIO(new_str))  # comments not used (only for global idf parse)
                assert len(records) == 1, "Wrong number of records created: %i" % len(records)
                new_record = records[0]
                created_records.append(self._dev_add_naive_record(new_record, position=position))

        return created_records

    # remove records
    @clear_cache
    def remove(self, record, raise_if_pointed=True):
        """
        Parameters
        ----------
        record: record
        raise_if_pointed if True, will raise IsPointedError if the deleted object is pointed by other records

        Raises
        ------
        IsPointedError
        """
        self.batch_remove([record], raise_if_pointed=raise_if_pointed)

    @clear_cache
    def batch_remove(self, records, raise_if_pointed=True):
        """
        removes records from idf

        Parameters
        ----------
        records: list of records
        raise_if_pointed: if True, will raise IsPointedError if the deleted object is pointed by other records

        Raises
        ------
        IsPointedError
        """
        # remove all
        with self.is_under_construction():
            for record in records:
                # check if record is pointed, if asked
                pointing_links_l = record._get_pointing_links()
                if len(pointing_links_l) > 0 and raise_if_pointed:
                    raise IsPointedError(
                        "Can't remove record if other records are pointing to it. "
                        "Pointing records: '%s'\nYou may use record.unlink_pointing_records() to remove all pointing."
                        % [o for (o, i) in pointing_links_l]
                    )

                # delete obsolete attributes
                record._neutralize()

                # remove from idf
                index = self._records.index(record)
                del self._records[index]

    # optimization
    @contextmanager
    def is_under_construction(self):
        """
        Allows the user to deactivate new reference checks while adding records. The whole idf is checked afterwards.
        This allows to construct idfs more efficiently.
        """
        self._constructing_mode_counter += 1
        yield
        self._constructing_mode_counter -= 1
        if self._constructing_mode_counter == 0:
            self._check_duplicate_references()

    # introspection
    def has_record(self, record):
        return record in self._records

    def get_info(self, sort_by_group=False, detailed=False):
        """
        Arguments
        ---------
        sort_by_group: will sort record descriptors by group
        detailed: will give all record descriptors' associated tags
        Returns
        -------
        a text describing the information on record contained in idd file
        """

        # rds: records descriptors
        def _get_rds_info(_ods, _line_start=""):
            _msg = ""
            for _rd in sorted(_ods, key=lambda x: x.table_ref):
                _msg += "\n%s%s" % (_line_start, _rd.table_ref)
                if detailed:
                    for _tag in _rd.tags:
                        _msg += "\n%s\t* %s: %s" % (_line_start, _tag, _rd.get_tag(_tag))
            return _msg

        rds_refs_set = set([record.get_table_ref() for record in self._records])
        name = "Idf: '%s'" % self._dev_path
        msg = "%s\n%s\n%s" % ("-" * len(name), name, "-" * len(name))
        if sort_by_group:
            for group_name in self._dev_idd.group_names:
                ods_l = []
                for od in self._dev_idd.get_record_descriptors_by_group(group_name):
                    if od.table_ref in rds_refs_set:
                        ods_l.append(od)
                if len(ods_l) > 0:
                    msg += "\nGroup - %s" % group_name
                    msg += _get_rds_info(ods_l, _line_start="\t")
        else:
            msg += _get_rds_info([self._dev_idd.get_record_descriptor(od_ref) for od_ref in rds_refs_set])

        return msg

    # export
    def copy(self, add_copyright=True):
        content = self.to_str(add_copyright=add_copyright)
        return self.__class__(content, self.idd, encoding=self._encoding)

    def to_str(self, style=None, add_copyright=True, sort=True, with_chapters=True):
        if style is None:
            style = style_library[CONF.default_write_style]
        if isinstance(style, IdfStyle):
            style = style
        elif isinstance(style, str):
            if style in style_library.keys():
                style = style_library[style]
            else:
                style = style_library[CONF.default_write_style]
        else:
            style = style_library[CONF.default_write_style]
        content = ""

        # idf comments
        idf_comment = self._head_comments
        if add_copyright:
            msg = self.copyright_comment()
            if msg not in idf_comment:
                idf_comment = msg + "\n" + idf_comment

        for comment in idf_comment.split("\n")[:-1]:
            content += style.get_head_comment(comment)

        # prepare records content [(table_ref, record_str), ...]
        formatted_records = [
            (obj.get_table_ref(), "\n%s" % obj.to_str(style="idf", idf_style=style)) for obj in self._records
        ]

        # sort if asked
        if sort:
            formatted_records = sorted(formatted_records)

        # iter
        current_ref = None
        for (record_ref, record_str) in formatted_records:
            # write chapter title if needed
            if with_chapters and (record_ref != current_ref):
                current_ref = record_ref
                content += "\n" + style.get_chapter_title(current_ref)

            # write record
            content += record_str

        return content

    def save_as(self, file_or_path, style=None, add_copyright=True, sort=True, with_chapters=True):
        is_path = isinstance(file_or_path, str)
        f = open(file_or_path, "w", encoding=self._encoding) if is_path else file_or_path
        try:
            f.write(self.to_str(
                style=style,
                add_copyright=add_copyright,
                sort=sort,
                with_chapters=with_chapters
            ))
        finally:
            if is_path:
                f.close()
