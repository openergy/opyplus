import uuid
import io

from ..configuration import CONF
from .exceptions import ObsoleteRecordError, IsPointedError, BrokenIdfError
from .cache import CachedMixin, clear_cache, cached
from .style import style_library, IdfStyle
from .multi_table_queryset import MultiTableQueryset


class Record(CachedMixin):
    _frozen = False  # for __setattr__ management

    # style
    _COMMENT_COLUMN_START = 35
    _TAB_LEN = 4
    _ROWS_NB = 120

    # raw_value and comment
    _RAW_VALUE = 0
    _COMMENT = 1

    def __init__(self, table, data=None, comments=None, head_comment=None, tail_comment=None):
        """
        Parameters
        ----------
        table
        data: dict, default {}
            key: index_or_ref, value: raw value or value
        comments: dict, default {}
            key: index_or_ref, value: raw value or value
        head_comment: str, default ""
        tail_comment: str, default ""
        """
        self._table = table
        self._head_comment = "" if head_comment is None else str(head_comment)
        self._tail_comment = "" if tail_comment is None else str(tail_comment)


        self._fields_l = []  # [[raw_value, comment], ...]

        self._descriptor = self.get_idf()._dev_idd.get_record_descriptor(table.get_ref())
        self._frozen = True

    # manage obsolescence
    def _check_obsolescence(self):
        if self._table is None:
            raise ObsoleteRecordError(
                "current record is obsolete (has been removed from it's idf), can't use it)")

    @clear_cache
    def _neutralize(self):
        """
        remove values and links of fields, idf, descriptor, pointing_d.
        """
        self._check_obsolescence()

        self._table = None
        self._descriptor = None

    # get info
    @property
    def _dev_fields_nb(self):
        # todo: document
        self._check_obsolescence()
        return max(
            len(self._descriptor.field_descriptors_l),
            max(self._data.keys())
        )

    # def _get_name(self):
    #     self._check_obsolescence()
    #     field0_name = self._descriptor.get_field_name(0)
    #     if (field0_name is None) or ("name" not in field0_name.lower()):
    #         return None
    #     return self._get_value(0)

    def _get_field_index(self, field_index_or_ref):
        """
        Returns field index (>=0).

        Raises
        ------
        AttributeError
        """
        self._check_obsolescence()

        if isinstance(field_index_or_ref, int):
            field_index_or_ref = (
                field_index_or_ref if field_index_or_ref >= 0 else
                self._dev_fields_nb + field_index_or_ref
            )
        return self._descriptor.get_field_index(field_index_or_ref)

    def _get_value(self, field_index_or_ref):
        """
        Parameters
        ----------
        field_index_or_ref

        Raises
        ------
        AttributeError
        """
        # parsed value and/or record
        self._check_obsolescence()

        index = self._get_field_index(field_index_or_ref)
        raw_value = self._fields_l[index][self._RAW_VALUE]
        fieldd = self._descriptor.get_field_descriptor(index)

        if fieldd.detailed_type in (fieldd.BASIC_FIELDS + ("reference",)):
            value, pointed_index = fieldd.basic_parse(raw_value), None

        elif fieldd.detailed_type == "object-list":
            value, pointed_index = self.get_idf()._dev_get_pointed_link(self.get_table_ref(), index, raw_value)

        else:
            raise NotImplementedError("Unknown field type : '%s'." % fieldd.detailed_type)
        return value

    def _dev_iter_raw_values(self):
        return (field[0] for field in self._fields_l)

    # set fields
    def _cleanup_and_check_raw_value(self, fieldd, raw_value):
        try:
            return fieldd.cleanup_and_check_raw_value(raw_value)
        except Exception as e:
            raise ValueError(
                f"Error while parsing field '{fieldd.name}', value '{raw_value}'. "
                f"Table: {self.get_table_ref()}. Error message:\n{str(e)}."
            ) from None

    @clear_cache
    def _set_raw_value(self, field_index_or_ref, raw_value_or_value, manage_pointed="yes"):
        """
        Parameters
        ----------
        field_index_or_ref
        raw_value_or_value
        manage_pointed: str, default "yes"
            "yes": unlink/re-link pointing
            "no": don't check (!! for initial loading only)
            "raise": raise if pointed
        """
        # prepare
        field_index = self._get_field_index(field_index_or_ref)
        field_descriptor = self._descriptor.get_field_descriptor(field_index)

        # if reference field is set, must update pointing (depending on manage_pointed option)
        pointing_links_to_update = []

        # transform to raw_value
        if field_descriptor.detailed_type in field_descriptor.BASIC_FIELDS:
            # basic type: we already have raw value
            raw_value = raw_value_or_value
        elif field_descriptor.detailed_type == "reference":
            # find pointing links
            pointing_links_to_update = self._get_pointing_links(field_index)

            # raise if asked and relevant
            if (manage_pointed == "raise") and len(pointing_links_to_update) > 0:
                raise IsPointedError(
                    "Set field is already pointed by another record. "
                    "First remove this record, or choose yes or no as manage_pointed option."
                )

            # reference: we already have raw value
            raw_value = raw_value_or_value
#        elif field_descriptor.detailed_type == "object-list":




    @clear_cache
    def _set_value(self, field_index_or_ref, raw_value_or_value, raise_if_pointed=False):
        self._check_obsolescence()

        field_index = self._get_field_index(field_index_or_ref)
        fieldd = self._descriptor.get_field_descriptor(field_index)

        if fieldd.detailed_type in fieldd.BASIC_FIELDS:  # basic type
            # transform None to ""
            if raw_value_or_value is None:
                raw_value_or_value = ""

            # cleanup
            raw_value = self._cleanup_and_check_raw_value(fieldd, str(raw_value_or_value))

            # set
            self._fields_l[field_index][self._RAW_VALUE] = raw_value

        elif fieldd.detailed_type == "reference":
            if raise_if_pointed:
                if len(self._get_pointing_links(field_index)) > 0:
                    raise IsPointedError(
                        "Set field is already pointed by another record. "
                        "First remove this record, or disable 'raise_if_pointed' argument."
                    )

            # remove all pointing
            pointing_links_l = self._get_pointing_links(field_index)
            for pointing_record, pointing_index in pointing_links_l:
                pointing_record[pointing_index] = None

            # cleanup
            raw_value = self._cleanup_and_check_raw_value(fieldd, str(raw_value_or_value))

            # store
            self._fields_l[field_index][self._RAW_VALUE] = raw_value

            # re-set all pointing
            for pointing_record, pointing_index in pointing_links_l:
                pointing_record[pointing_index] = self

        elif fieldd.detailed_type == "object-list":  # detailed type
            # convert to record if necessary
            if raw_value_or_value is None:
                self._fields_l[field_index][self._RAW_VALUE] = self._cleanup_and_check_raw_value(fieldd, None)
            else:
                if isinstance(raw_value_or_value, str):
                    try:
                        value = self.get_idf().add_from_string(raw_value_or_value)
                    except BrokenIdfError as e:
                        raise e
                elif isinstance(raw_value_or_value, Record):
                    value = raw_value_or_value
                else:
                    raise ValueError("Wrong value descriptor: '%s' (instead of IdfObject)." % type(raw_value_or_value))

                # check if correct idf
                assert value.get_idf() is self.get_idf(), \
                    "Given record does not belong to correct idf: " \
                        f"'{value.get_idf()._dev_path}' instead of '{self.get_idf()._dev_path}'."

                # check that new record ref can be set, and find pointed index
                pointed_index = None
                for link_name in fieldd.get_tag("object-list"):
                    # link: (record_ref, index)
                    if pointed_index is not None:
                        break
                    for record_descriptor, record_index in self.get_idf()._dev_idd.pointed_links(link_name):
                        if (
                                (value.get_table_ref() == record_descriptor.table_ref) and
                                (value._get_value(record_index) is not None)
                        ):
                            # ok, we fond an accepted combination
                            pointed_index = record_index
                            break
                assert pointed_index is not None, \
                    f"Wrong value ref: '{value.get_table_ref()}' for field '{field_index}' " \
                        f"of record descriptor ref '{self.get_table_ref()}'. Can't set record."

                # get raw value
                raw_value = value.get_raw_value(pointed_index)

                # now we checked everything was ok, we remove old field (so pointed record unlinks correctly)
                self._fields_l[field_index][self._RAW_VALUE] = self._cleanup_and_check_raw_value(fieldd, None)

                # store and parse
                self._fields_l[field_index][self._RAW_VALUE] = raw_value
        else:
            raise ValueError("Unknown detailed type: '%s'." % fieldd.detailed_type)

    # pointing
    @clear_cache
    def _dev_clear_pointing_fields(self, only_on_pointed_record=None):
        """
        Removes all fields that point

        Parameters
        ----------
        only_on_pointed_record: record, default None
            if not None, only fields pointing on only_on_pointed_record will be cleared
        """
        self._check_obsolescence()
        for i in range(len(self._fields_l)):
            fieldd = self._descriptor.get_field_descriptor(i)
            if fieldd.detailed_type == "object-list":
                if (only_on_pointed_record is None) or (self._get_value(i) is only_on_pointed_record):
                    self._set_value(i, None)

    @cached
    def _get_pointing_links(self, field_index_or_name=None):
        index_l = (
            range(len(self._fields_l)) if field_index_or_name is None else [self._get_field_index(field_index_or_name)]
        )

        all_pointing_links = []
        for i in index_l:
            fieldd = self._descriptor.get_field_descriptor(i)
            if fieldd.detailed_type != "reference":
                continue
            all_pointing_links.extend(self.get_idf()._dev_get_pointing_links(self.get_table_ref(), i, self.get_raw_value(i)))

        return all_pointing_links

    # ------------------------------------------------ api -------------------------------------------------------------
    # python magic
    def __getitem__(self, item):
        """
        Arguments
        ---------
        item: field index or name [or slice of field indexes and/or names]
        """
        if isinstance(item, slice):
            start = 0 if item.start is None else self._get_field_index(item.start)
            stop = len(self) if item.stop is None else min(self._get_field_index(item.stop), len(self))
            step = item.step or 1
            return [self._get_value(i) for i in range(start, stop, step)]
        elif isinstance(item, int):
            return self._get_value(item)
        raise TypeError("item must be an integer or a slice")

    def __getattr__(self, item):
        return self._get_value(item)

    def __setitem__(self, index, value):
        """
        Arguments
        ---------
        index: field index
        value: raw, parsed or record value (see get_value documentation)
        """
        self._set_value(index, value)

    def __setattr__(self, name, value):
        """
        Parameters
        ----------
        name: field ref
        value: raw, parsed or record value (see get_value documentation)
        """
        # manage __init__
        if not self._frozen:
            return super().__setattr__(name, value)

        # object attribute
        if name in self.__dict__:
            return super().__setattr__(name, value)

        # set eplus value
        self._set_value(name, value)

    def __len__(self):
        return self._dev_fields_nb

    def __iter__(self):
        """
        Iter through fields of record.
        """
        return (self[i] for i in range(len(self)))

    def __lt__(self, other):
        return tuple(self._dev_iter_raw_values()) <= tuple(other._dev_iter_raw_values())

    def __str__(self):
        return self.to_str(style="console")

    def __repr__(self):
        name = self._get_name()
        return f"<{self.get_table_ref()}>" if name is None else f"<{self.get_table_ref()}: {name}>"

    # get/set on records fields
    def get_raw_value(self, field_index_or_name):
        self._check_obsolescence()

        field_index = self._get_field_index(field_index_or_name)

        return self._fields_l[field_index][self._RAW_VALUE]

    @clear_cache
    def add_field(self, raw_value_or_value, comment=""):
        """
        Add a new field to record (at the end).
        Parameters
        ----------
        raw_value_or_value:
            see get_value for mor information
        comment:
            associated comment
        Returns
        -------
        """
        self._check_obsolescence()

        # get field descriptor
        fieldd = self._descriptor.get_field_descriptor(self._dev_fields_nb)

        # cleanup
        raw_value = self._cleanup_and_check_raw_value(fieldd, raw_value_or_value)

        # append
        self._fields_l.append([raw_value, comment])

    @clear_cache
    def replace_values(self, new_record_str):
        """
        Replaces all values of record that are not links (neither pointing nor pointed fields) with values contained
        in the idf record string 'new_record_str'.
        """
        self._check_obsolescence()

        # create record (but it will not be linked to idf)
        records_l, comments = self.get_idf()._dev_parse(io.StringIO(new_record_str))  # comments not used
        assert len(records_l) == 1, "Wrong number of records created: %i" % len(records_l)
        new_record = records_l[0]

        assert self.get_table_ref() == new_record.get_table_ref(), \
            f"New record ({self.get_table_ref()}) does not have same reference as " \
                f"new record ({new_record.get_table_ref()}). Can't replace."

        # replace fields using raw_values, one by one
        old_nb, new_nb = self._dev_fields_nb, new_record._dev_fields_nb

        for i in range(max(old_nb, new_nb)):
            fieldd = self._descriptor.get_field_descriptor(i)

            if fieldd.detailed_type in ("reference", "object-list"):
                continue  # we do not modify links

            if (i < old_nb) and (i < new_nb):
                self._set_value(i, new_record.get_raw_value(i))
            elif i < old_nb:
                self._set_value(i, None)
            else:
                self.add_field(new_record.get_raw_value(i), new_record.get_field_comment(i))

        # remove all last values
        self._fields_l = self._fields_l[:new_nb]

    @clear_cache
    def pop(self, field_index_or_name=-1):
        """
        Removes field from idf record and shift following rows upwards (value and comment will be removed).
        Can only be applied on extensible fields (for now, only extensible:1).

        Parameters
        ---------
        index: index of field to remove (default -1)

        Returns
        -------
        Value of popped field.

        Raises
        ------
        RuntimeError
        """
        self._check_obsolescence()

        # check extensible
        cycle_start, cycle_len, _ = self._descriptor.extensible_info
        if cycle_len != 1:
            raise RuntimeError("Can only use pop on extensible:1 fields.")

        # check index
        pop_index = self._get_field_index(field_index_or_name)
        if pop_index < cycle_start:
            raise RuntimeError("Pop index must be >= cycle start index.")

        # store value
        pop_value = self._get_value(pop_index)

        # remove field
        self._fields_l.pop(pop_index)

        return pop_value

    # get/set on comments
    def get_field_comment(self, field_index_or_name):
        self._check_obsolescence()

        field_index = self._get_field_index(field_index_or_name)
        comment = self._fields_l[field_index][self._COMMENT]
        return "" if comment is None else comment

    @clear_cache
    def set_field_comment(self, field_index_or_name, comment):
        self._check_obsolescence()

        field_index = self._get_field_index(field_index_or_name)
        comment = None if comment.strip() == "" else str(comment).replace("\n", " ").strip()
        self._fields_l[field_index][self._COMMENT] = comment

    def get_head_comment(self):
        self._check_obsolescence()
        return "" if self._head_comment is None else self._head_comment

    @clear_cache
    def set_head_comment(self, comment):
        """
        All line return will be replaced by a blank.
        """
        self._check_obsolescence()

        comment = None if comment.strip() == "" else str(comment).replace("\n", " ").strip()
        self._head_comment = comment

    def get_tail_comment(self):
        self._check_obsolescence()
        return "" if self._tail_comment is None else self._tail_comment

    @clear_cache
    def set_tail_comment(self, comment):
        self._check_obsolescence()
        comment = None if comment.strip() == "" else str(comment).strip()
        self._tail_comment = comment

    # copy
    def copy(self):
        self._check_obsolescence()
        # create new record
        new_record = self.get_idf()._dev_record_cls(
            self._table,
            head_comment=self._head_comment,
            tail_comment=self._tail_comment
        )
        # we must change all references
        for i in range(len(self._fields_l)):
            fieldd = self._descriptor.get_field_descriptor(i)
            if fieldd.detailed_type == "reference":
                raw_value = str(uuid.uuid4())  # dt.datetime.now().strftime("%Y%m%d%H%M%S%f-") + str(i)
            else:
                raw_value = self.get_raw_value(i)
            new_record.add_field(raw_value, comment=self.get_field_comment(i))

        # add record to idf
        return self.get_idf()._dev_add_naive_record(new_record)

    # structure
    def get_idf(self):
        return self._table.get_epm()

    def get_table(self):
        """
        Record descriptor ref
        """
        self._check_obsolescence()
        return self._table

    def get_table_ref(self):
        return self._table.get_ref()

    # links
    @cached
    def get_pointing_records(self):
        self._check_obsolescence()
        return MultiTableQueryset(
            self.get_idf(),
            [pointing_record for pointing_record, pointing_index in self._get_pointing_links()]
        )

    @cached
    def get_pointed_records(self, field_index_or_name=None):
        """
        not used, not tested
        """
        self._check_obsolescence()

        index_l = (
            range(len(self._fields_l)) if field_index_or_name is None else [self._get_field_index(field_index_or_name)])

        records = []
        for i in index_l:
            value = self._get_value(i)
            if isinstance(value, Record):
                records.append(value)

        return MultiTableQueryset(self.get_idf(), records)

    @clear_cache
    def unlink_pointing_records(self):
        self._check_obsolescence()
        # remove from pointing
        for pointing_record, pointing_index in self._get_pointing_links():
            pointing_record._dev_clear_pointing_fields(only_on_pointed_record=self)

    # info
    def get_info(self, how="txt"):
        """
        Returns a string with all available fields of record (information provided by the idd).

        Arguments
        ---------
        how: str
            txt, dict
        """
        self._check_obsolescence()
        return self._descriptor.get_info(how=how)

    # export
    def to_str(self, style="idf", idf_style=None):
        self._check_obsolescence()

        if style in ("idf", "console"):
            if idf_style is None:
                idf_style = style_library[CONF.default_write_style]
            if isinstance(idf_style, IdfStyle):
                idf_style = idf_style
            elif isinstance(idf_style, str):
                if idf_style in style_library.keys():
                    idf_style = style_library[style]
                else:
                    idf_style = style_library[CONF.default_write_style]
            else:
                idf_style = style_library[CONF.default_write_style]
            # record descriptor ref
            content = "%s" % self._descriptor.table_name + ("," if self._dev_fields_nb != 0 else ";")
            spaces_nb = self._COMMENT_COLUMN_START - len(content)
            if spaces_nb < 0:
                spaces_nb = self._TAB_LEN

            s = ""

            # Tail comment if the type is before the record
            if idf_style.tail_type == "before":
                if self._tail_comment:
                    s += "\n"
                    for line in self._tail_comment.strip().split("\n"):
                        s += idf_style.get_tail_record_comment(line)

            # MANAGE HEAD COMMENT
            if self._head_comment:
                comment = "%s" % (" " * spaces_nb) + idf_style.get_record_comment(
                    self._head_comment,
                    line_jump=False
                )
            else:
                comment = ""
            s += content + comment + "\n"

            # fields
            for field_index, (f_raw_value, f_comment) in enumerate(self._fields_l):
                content = "%s%s%s" % (
                    " " * self._TAB_LEN,
                    f_raw_value,
                    ";" if field_index == len(self._fields_l)-1 else ","
                )
                spaces_nb = self._COMMENT_COLUMN_START - len(content)
                if spaces_nb < 0:
                    spaces_nb = self._TAB_LEN

                # MANAGE FIELD COMMENT
                if f_comment:
                    comment = (" " * spaces_nb) + idf_style.get_record_comment(
                        f_comment,
                        line_jump=False
                    )
                else:
                    comment = ""
                s += content + comment + "\n"

            # Tail comment if the type is after the record
            if idf_style.tail_type == "after":
                if self._tail_comment:
                    s += "\n"
                    for line in self._tail_comment.strip().split("\n"):
                        s += idf_style.get_tail_record_comment(line)
        else:
            raise ValueError("Unknown style: '%s'." % style)

        return s
