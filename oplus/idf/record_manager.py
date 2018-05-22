import io
import uuid

from oplus import CONF
from .record import Record
from .cache import clear_cache, cached
from .queryset import Queryset
from .exceptions import IsPointedError, BrokenIdfError, ObsoleteRecordError
from .style import style_library, IdfStyle


class RecordManager:
    """
    raw_values are always strings, and are enforced lowercase
    """
    record_cls = Record  # for subclassing

    _COMMENT_COLUMN_START = 35
    _TAB_LEN = 4
    _ROWS_NB = 120

    _RAW_VALUE = 0
    _COMMENT = 1

    def __init__(self, ref, idf_manager, head_comment=None, tail_comment=None):
        self._table_ref = ref
        self._table = idf_manager.get_table(ref)
        self._head_comment = head_comment
        self._tail_comment = tail_comment
        self._fields_l = []  # [[raw_value, comment], ...]

        self._idf_manager = idf_manager
        self._descriptor = self._idf_manager.idd.get_record_descriptor(ref)

        self._record = self.record_cls(self)

    def _check_obsolescence(self):
        if self._idf_manager is None:
            raise ObsoleteRecordError(
                "current record is obsolete (has been removed from it's idf), can't use it)")

    def _cleanup_and_check_raw_value(self, fieldd, raw_value):
        try:
            return fieldd.cleanup_and_check_raw_value(raw_value)
        except Exception as e:
            raise ValueError(
                f"Error while parsing field '{fieldd.name}', value '{raw_value}'. "
                f"Table: {self.table.ref}. Error message:\n{str(e)}."
            ) from None

    # ---------------------------------------------- EXPOSE -----------------------------------------------------------
    @property
    def table(self):
        self._check_obsolescence()
        return self._table

    @property
    def record(self):
        self._check_obsolescence()
        return self._record

    @property
    def fields_nb(self):
        self._check_obsolescence()
        return len(self._fields_l)

    @property
    def idf_manager(self):
        self._check_obsolescence()
        return self._idf_manager

    def get_name(self):
        self._check_obsolescence()
        field0_name = self._descriptor.get_field_name(0)
        if (field0_name is None) or ("name" not in field0_name.lower()):
            return None
        return self.get_value(0)

    # --------------------------------------------- CONSTRUCT ----------------------------------------------------------
    @clear_cache
    def add_field(self, raw_value, comment=""):
        self._check_obsolescence()

        # get field descriptor
        fieldd = self._descriptor.get_field_descriptor(self.fields_nb)

        # cleanup
        raw_value = self._cleanup_and_check_raw_value(fieldd, raw_value)

        # append
        self._fields_l.append([raw_value, comment])

    @clear_cache
    def add_tail_comment(self, comment):
        self._check_obsolescence()
        stripped = comment.strip()
        if stripped == "":
            return None
        if self._tail_comment is None:
            self._tail_comment = ""
        self._tail_comment += "%s\n" % stripped

    def copy(self):
        self._check_obsolescence()
        # create new record
        new_record_manager = self._idf_manager.record_manager_cls(
            self._table_ref,
            self._idf_manager,
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
            new_record_manager.add_field(raw_value, comment=self.get_field_comment(i))

        # add record to idf
        return self._idf_manager.add_naive_record(new_record_manager.record)

    # ---------------------------------------------- DESTROY -----------------------------------------------------------
    @clear_cache
    def clear_pointing_fields(self, only_on_pointed_record=None):
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
                if (only_on_pointed_record is None) or (self.get_value(i) is only_on_pointed_record):
                    self.set_value(i, None)

    @clear_cache
    def unlink_pointing_records(self):
        self._check_obsolescence()
        # remove from pointing
        for pointing_record, pointing_index in self.get_pointing_links():
            pointing_record._.clear_pointing_fields(only_on_pointed_record=self.record)

    @clear_cache
    def neutralize(self):
        """
        remove values and links of fields, idf_manager, descriptor, pointing_d.
        """
        self._check_obsolescence()

        self._idf_manager = None
        self._descriptor = None

    @clear_cache
    def pop(self, field_index_or_name=-1):
        """
        Remove item at given position and return it. All rows will be shifted upwards to fill the blank. May only be
        used on extensible fields.
        For the moment, only extensible=1 is coded.
        """
        self._check_obsolescence()

        # check extensible
        extensible_cycle_len, extensible_start_index = self._descriptor.extensible
        assert extensible_cycle_len == 1, "Can only use pop on fields defined as 'extensible:1'."

        # check index
        pop_index = self.get_field_index(field_index_or_name)
        assert pop_index >= extensible_start_index, \
            "Can only use pop on extensible fields (pop index must be > than extensible start index)."

        # store value
        pop_value = self.get_value(pop_index)

        # remove field
        self._fields_l.pop(pop_index)

        return pop_value

    # ------------------------------------------------ GET -------------------------------------------------------------
    def get_field_index(self, field_index_or_insensitive_name):
        """
        Returns field index (>=0).
        """
        self._check_obsolescence()

        if isinstance(field_index_or_insensitive_name, int):
            field_index_or_insensitive_name = (
                field_index_or_insensitive_name if field_index_or_insensitive_name >= 0 else
                self.fields_nb + field_index_or_insensitive_name
            )
        return self._descriptor.get_field_index(field_index_or_insensitive_name)

    def get_raw_value(self, field_index_or_name):
        self._check_obsolescence()

        field_index = self.get_field_index(field_index_or_name)

        return self._fields_l[field_index][self._RAW_VALUE]

    def get_value(self, field_index_or_insensitive_name):
        # parsed value and/or record
        self._check_obsolescence()

        index = self.get_field_index(field_index_or_insensitive_name)
        raw_value = self._fields_l[index][self._RAW_VALUE]
        fieldd = self._descriptor.get_field_descriptor(index)

        if fieldd.detailed_type in (fieldd.BASIC_FIELDS + ("reference",)):
            value, pointed_index = fieldd.basic_parse(raw_value), None

        elif fieldd.detailed_type == "object-list":
            value, pointed_index = self._idf_manager.get_pointed_link(self._table_ref, index, raw_value)

        else:
            raise NotImplementedError("Unknown field type : '%s'." % fieldd.detailed_type)
        return value

    def get_field_comment(self, field_index_or_name):
        self._check_obsolescence()

        field_index = self.get_field_index(field_index_or_name)
        comment = self._fields_l[field_index][self._COMMENT]
        return "" if comment is None else comment

    def get_head_comment(self):
        self._check_obsolescence()
        return "" if self._head_comment is None else self._head_comment

    def get_tail_comment(self):
        self._check_obsolescence()
        return "" if self._tail_comment is None else self._tail_comment

    @cached
    def get_pointing_links(self, field_index_or_name=None):
        index_l = (
            range(len(self._fields_l)) if field_index_or_name is None else [self.get_field_index(field_index_or_name)]
        )

        all_pointing_links = []
        for i in index_l:
            fieldd = self._descriptor.get_field_descriptor(i)
            if fieldd.detailed_type != "reference":
                continue
            all_pointing_links.extend(self.idf_manager.get_pointing_links(self._table_ref, i, self.get_raw_value(i)))

        return all_pointing_links

    @property
    @cached
    def pointing_records(self):
        self._check_obsolescence()
        return Queryset([pointing_record for pointing_record, pointing_index in self.get_pointing_links()])

    # def get_pointed_links_l(self, field_index_or_name=None):
    #     """
    #     not used, not tested
    #     """
    #     index_l = (range(len(self._fields_l)) if field_index_or_name is None
    #                else [self.get_field_index(field_index_or_name)])
    #     links_l = []
    #     for i in index_l:
    #         value = self._fields_l[i][self._VALUE]
    #         if isinstance(value, IdfObject):
    #             links_l.append((value, self._fields_l[i][self._POINTED_INDEX]))
    #
    #     return links_l

    @cached
    def get_pointed_records(self, field_index_or_name=None):
        """
        not used, not tested
        """
        self._check_obsolescence()

        index_l = (
            range(len(self._fields_l)) if field_index_or_name is None else [self.get_field_index(field_index_or_name)])

        records = []
        for i in index_l:
            value = self.get_value(i)
            if isinstance(value, Record):
                records.append(value)

        return Queryset(records)

    # ------------------------------------------------ SET -------------------------------------------------------------
    @clear_cache
    def set_value(self, field_index_or_name, raw_value_or_value, raise_if_pointed=False):
        self._check_obsolescence()

        field_index = self.get_field_index(field_index_or_name)
        fieldd = self._descriptor.get_field_descriptor(field_index)

        if fieldd.detailed_type in fieldd.BASIC_FIELDS:  # basic type
            # cleanup
            raw_value = self._cleanup_and_check_raw_value(fieldd, str(raw_value_or_value))

            # set
            self._fields_l[field_index][self._RAW_VALUE] = raw_value

        elif fieldd.detailed_type == "reference":
            if raise_if_pointed:
                if len(self.get_pointing_links(field_index)) > 0:
                    raise IsPointedError(
                        "Set field is already pointed by another record. "
                        "First remove this record, or disable 'raise_if_pointed' argument."
                    )

            # remove all pointing
            pointing_links_l = self.get_pointing_links(field_index)
            for pointing_record, pointing_index in pointing_links_l:
                pointing_record._.set_value(pointing_index, None)

            # cleanup
            raw_value = self._cleanup_and_check_raw_value(fieldd, str(raw_value_or_value))

            # store
            self._fields_l[field_index][self._RAW_VALUE] = raw_value

            # re-set all pointing
            for pointing_record, pointing_index in pointing_links_l:
                pointing_record._.set_value(pointing_index, self._record)

        elif fieldd.detailed_type == "object-list":  # detailed type
            # convert to record if necessary
            if raw_value_or_value is None:
                self._fields_l[field_index][self._RAW_VALUE] = self._cleanup_and_check_raw_value(fieldd, None)
            else:
                if isinstance(raw_value_or_value, str):
                    try:
                        value = self._idf_manager.add_records(raw_value_or_value)
                    except BrokenIdfError as e:
                        raise e
                elif isinstance(raw_value_or_value, Record):
                    value = raw_value_or_value
                else:
                    raise ValueError("Wrong value descriptor: '%s' (instead of IdfObject)." % type(raw_value_or_value))

                # check if correct idf
                assert value._.idf_manager is self._idf_manager, \
                    "Given record does not belong to correct idf: " \
                    f"'{value._.idf_manager.path}' instead of '{self._idf_manager.path}'."

                # check that new record ref can be set, and find pointed index
                pointed_index = None
                for link_name in fieldd.get_tag("object-list"):
                    # link: (record_ref, index)
                    if pointed_index is not None:
                        break
                    for record_descriptor, record_index in self._idf_manager.idd.pointed_links(link_name):
                        if (
                                (value._.table.ref == record_descriptor.table_ref) and
                                (value._.get_value(record_index) is not None)
                        ):
                            # ok, we fond an accepted combination
                            pointed_index = record_index
                            break
                assert pointed_index is not None, \
                    f"Wrong value ref: '{value._.table.ref}' for field '{field_index}' " \
                    f"of record descriptor ref '{self._table_ref}'. Can't set record."

                # get raw value
                raw_value = value._.get_raw_value(pointed_index)

                # now we checked everything was ok, we remove old field (so pointed record unlinks correctly)
                self._fields_l[field_index][self._RAW_VALUE] = self._cleanup_and_check_raw_value(fieldd, None)

                # store and parse
                self._fields_l[field_index][self._RAW_VALUE] = raw_value
        else:
            raise ValueError("Unknown detailed type: '%s'." % fieldd.detailed_type)

    @clear_cache
    def replace_values(self, new_record_str):
        """
        Purpose: keep old pointed links
        """
        self._check_obsolescence()

        # create record (but it will not be linked to idf)
        records_l, comments = self._idf_manager.parse(io.StringIO(new_record_str))  # comments not used
        assert len(records_l) == 1, "Wrong number of records created: %i" % len(records_l)
        new_record = records_l[0]

        assert self._table_ref == new_record._.table.ref, \
            f"New record ({self._table_ref}) does not have same reference as new record ({new_record._.table.ref}). " \
            f"Can't replace."

        # replace fields using raw_values, one by one
        old_nb, new_nb = self.fields_nb, new_record._.fields_nb

        for i in range(max(old_nb, new_nb)):
            fieldd = self._descriptor.get_field_descriptor(i)

            if fieldd.detailed_type in ("reference", "object-list"):
                continue  # we do not modify links

            if (i < old_nb) and (i < new_nb):
                self.set_value(i, new_record._.get_raw_value(i))
            elif i < old_nb:
                self.set_value(i, None)
            else:
                self.add_field(new_record._.get_raw_value(i), new_record._.get_field_comment(i))

        # remove all last values
        self._fields_l = self._fields_l[:new_nb]

    @clear_cache
    def set_field_comment(self, field_index_or_name, comment):
        self._check_obsolescence()

        field_index = self.get_field_index(field_index_or_name)
        comment = None if comment.strip() == "" else str(comment).replace("\n", " ").strip()
        self._fields_l[field_index][self._COMMENT] = comment

    @clear_cache
    def set_head_comment(self, comment):
        """
        All line return will be replaced by a blank.
        """
        self._check_obsolescence()

        comment = None if comment.strip() == "" else str(comment).replace("\n", " ").strip()
        self._head_comment = comment

    @clear_cache
    def set_tail_comment(self, comment):
        self._check_obsolescence()

        comment = None if comment.strip() == "" else str(comment).strip()
        self._tail_comment = comment

    # ------------------------------------------------ COMMUNICATE -----------------------------------------------------
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
            content = "%s" % self._descriptor.table_ref + ("," if self.fields_nb != 0 else ";")
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

    def info(self, how=False):
        """
        Returns a string with all available fields of record (information provided by the idd).

        Parameters
        ----------
        how: str
            txt, dict
        """
        self._check_obsolescence()
        return self._descriptor.info(how=how)
