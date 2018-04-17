"""
IDF
---
We respect private/public naming conventions for methods and variables, EXCEPT for IDF or IDFObject managers. The
_manager variable is semi-private: it can be accessed by other managers (including other modules of oplus), but not by
IDF or IDFObject. The _manager attributes therefore remain private to oplus users.
"""
# todo: document

import io
import datetime as dt
from contextlib import contextmanager
import warnings


from oplus.configuration import CONF
from oplus.idd import IDD
from oplus.util import get_copyright_comment, get_string_buffer
from oplus.util import IDFStyle, style_library


class IDFError(Exception):
    pass


class BrokenIDFError(IDFError):
    pass


class IsPointedError(IDFError):
    pass


class ObjectDoesNotExist(IDFError):
    pass


class MultipleObjectsReturned(IDFError):
    pass


# ------------------------------------------------ CACHE MANAGEMENT -------------------------------------------------- #
def clear_cache(method):
    def wrapper(self, *args, **kwargs):
        if isinstance(self, IDFManager):
            idf_manager = self
        elif isinstance(self, IDFObjectManager):
            idf_manager = self.idf_manager
        else:
            raise ValueError("clear_cache decorator applied to a non cached item")
        idf_manager._deactivate_cache()
        res = method(self, *args, **kwargs)
        idf_manager._activate_cache()
        return res
    return wrapper


def cached(method):
    def wrapper(self, *args, **kwargs):
        if isinstance(self, IDFManager):
            cache = self.cache
        elif isinstance(self, IDFObjectManager):
            cache = self.idf_manager.cache
        else:
            raise ValueError("cached decorator applied to a non cached item")
        if cache is None:
            return method(self, *args, **kwargs)
        key = CacheKey(self, method, *args, **kwargs)
        if key not in cache:
            cache[key] = dict(value=method(self, *args, **kwargs), hits=0)
        else:
            cache[key]["hits"] += 1
        return cache[key]["value"]
    return wrapper


class Cached:
    cache = None  # dict(key: dict(value=v, hits=0))  (hits for testing)

    def _activate_cache(self):
        if self.cache is None:
            self.cache = {}

    # todo: remove this method at the next major update
    def activate_cache(self):
        warnings.warn(
            "activate_cache is deprecated and will be removed: the cache is now managed automatically",
            category=DeprecationWarning
        )

    def _deactivate_cache(self):
        self.cache = None

    # todo: remove this method at the next major update
    def deactivate_cache(self):
        warnings.warn(
            "deactivate_cache is deprecated and will be removed: the cache is now managed automatically",
            category=DeprecationWarning
        )

    def clear_cache(self):
        if self.cache is not None:
            self.cache = {}

    @property
    def is_cached(self):
        return self.cache is not None


class CacheKey:
    """
    emulated a dict that can store hashable types
    """
    def __init__(self, obj, method,  *args, **kwargs):
        self._value = tuple([obj, method] + list(args) + [(k, v) for k, v in sorted(kwargs.items())])

    def __hash__(self):
        return self._value.__hash__()

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __str__(self):
        return "<CacheKey: %s>" % str(self._value)

# ----------------------------------------------------------------------------------------------------------------------
# --------------------------------------------- IDF OBJECTS ------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


# ----------------------------------------------- idf object  ----------------------------------------------------------
class IDFObject:
    """
    IDFObject is allowed to access private keys/methods of IDF.
    """
    def __init__(self, object_manager):
        self._ = object_manager

    def __str__(self):
        """pretty prints"""
        return self._.to_str(style="console")

    def __repr__(self):
        """concise print"""
        return "<Idf object: %s>" % self.ref

    def __getitem__(self, item):
        """
        Arguments
        ---------
        item: field index or name [or slice of field indexes and/or names]
        """
        if isinstance(item, slice):
            start = 0 if item.start is None else self._.get_field_index(item.start)
            stop = len(self) if item.stop is None else min(self._.get_field_index(item.stop), len(self))
            step = item.step or 1
            return [self._.get_value(i) for i in range(start, stop, step)]
        return self._.get_value(item)

    def get(self, item, default=None):
        try:
            return self[item]
        except (AttributeError, IndexError):
            return default

    def __setitem__(self, key, value):
        """
        Arguments
        ---------
        key: field index or name
        value: field raw, parsed or object value (see get_value documentation)
        """
        self._.set_value(key, value)

    def __len__(self):
        return self._.fields_nb

    def __iter__(self):
        """
        Iter through fields of object.
        """
        def iter_var():
            for i in range(len(self)):
                yield self[i]
        return iter_var()

    @property
    def idf(self):
        return self._.idf_manager.idf

    @property
    def ref(self):
        """
        Object descriptor ref
        """
        return self._.ref

    @property
    def pointing_objects(self):
        return self._.pointing_objects

    def to_str(self, style="idf"):
        return self._.to_str(style=style)

    def info(self, detailed=False):
        """
        Returns a string with all available fields of object (information provided by the idd).
        Arguments
        ---------
        detailed: bool
            include all field tags information
        """
        return self._.info(detailed=detailed)

    def copy(self):
        return self._.copy()

    def add_field(self, raw_value_or_value, comment=""):
        """
        Add a new field to object (at the end).
        Parameters
        ----------
        raw_value_or_value:
            see get_value for mor information
        comment:
            associated comment
        Returns
        -------
        """
        self._.add_field("", comment=comment)
        self._.set_value(self._.fields_nb-1, raw_value_or_value)

    def replace_values(self, new_object_str):
        """
        Replaces all values of object that are not links (neither pointing nor pointed fields) with values contained
        in the idf object string 'new_object_str'.
        """
        self._.replace_values(new_object_str)

    def pop(self, index=-1):
        """
        Removes field from idf object and shift following rows upwards (value and comment will be removed).
        Can only be applied on extensible fields (for now, only extensible:1).
        #todo: manage extensible > 1
        Arguments
        ---------
        index: index of field to remove (default -1)
        Returns
        -------
        Value of poped field.
        """
        return self._.pop(index)

    def field_comment(self, field_index_or_name, comment=None):
        if comment is None:
            return self._.get_field_comment(field_index_or_name)
        self._.set_field_comment(field_index_or_name, comment)

    @property
    def head_comment(self):
        return self._.get_head_comment()

    @head_comment.setter
    def head_comment(self, value):
        self._.set_head_comment(value)

    @property
    def tail_comment(self):
        return self._.get_tail_comment()

    @tail_comment.setter
    def tail_comment(self, value):
        self._.set_tail_comment(value)


# ------------------------------------------- idf object manager -------------------------------------------------------
class IDFObjectManager:
    idf_object_cls = IDFObject  # for subclassing

    _COMMENT_COLUMN_START = 35
    _TAB_LEN = 4
    _ROWS_NB = 120

    _RAW_VALUE = 0
    _COMMENT = 1

    def __init__(self, ref, idf_manager, head_comment=None, tail_comment=None):
        self._ref = ref
        self._head_comment = head_comment
        self._tail_comment = tail_comment
        self._fields_l = []  # [[raw_value, comment], ...]

        self._idf_manager = idf_manager
        self._descriptor = self._idf_manager.idd.get_object_descriptor(ref)

        self._idf_object = self.idf_object_cls(self)

    # ---------------------------------------------- EXPOSE ------------------------------------------------------------
    @property
    def ref(self):
        return self._ref

    @property
    def idf_object(self):
        return self._idf_object

    @property
    def fields_nb(self):
        return len(self._fields_l)

    @property
    def idf_manager(self):
        return self._idf_manager

    # --------------------------------------------- CONSTRUCT ----------------------------------------------------------
    @clear_cache
    def add_field(self, raw_value, comment=""):
        if not isinstance(raw_value, str):
            raise IDFError("'raw_value' must be a string.")
        self._fields_l.append([raw_value, comment])

    @clear_cache
    def add_tail_comment(self, comment):
        stripped = comment.strip()
        if stripped == "":
            return None
        if self._tail_comment is None:
            self._tail_comment = ""
        self._tail_comment += "%s\n" % stripped

    def copy(self):
        # create new object
        new_object_manager = self._idf_manager.idf_object_manager_cls(
            self._ref,
            self._idf_manager,
            head_comment=self._head_comment,
            tail_comment=self._tail_comment
        )
        # we must change all references
        for i in range(len(self._fields_l)):
            fieldd = self._descriptor.get_field_descriptor(i)
            if fieldd.detailed_type == "reference":
                raw_value = dt.datetime.now().strftime("%Y%m%d%H%M%S%f") + str(i)
            else:
                raw_value = self.get_raw_value(i)
            new_object_manager.add_field(raw_value, comment=self.get_field_comment(i))

        # add object to idf
        return self._idf_manager.add_object_from_parsed(new_object_manager)

    # ---------------------------------------------- DESTROY -----------------------------------------------------------
    @clear_cache
    def remove_values_that_point(self, pointed_object=None):
        """
        Removes all fields that point at pointed_object if not None (if you want a specific index, use remove_value).
        """
        for i in range(len(self._fields_l)):
            fieldd = self._descriptor.get_field_descriptor(i)
            if fieldd.detailed_type == "object-list":
                if (pointed_object is None) or (self.get_value(i) is pointed_object):
                    self.set_value(i, None)

    @clear_cache
    def neutralize(self):
        """
        remove values and links of fields, idf_manager, descriptor, pointing_d.
        """
        self._idf_manager = None
        self._descriptor = None

    @clear_cache
    def pop(self, field_index_or_name=-1):
        """
        Remove item at given position and return it. All rows will be shifted upwards to fill the blank. May only be
        used on extensible fields.
        For the moment, only extensible=1 is coded.
        """
        # check extensible
        extensible_cycle_len, extensible_start_index = self._descriptor.extensible
        if extensible_cycle_len != 1:
            raise IDFError("Can only use pop on fields defined as 'extensible:1'.")

        # check index
        pop_index = self.get_field_index(field_index_or_name)
        if pop_index < extensible_start_index:
            raise IDFError("Can only use pop on extensible fields (pop index must be > than extensible start index).")

        # store value
        pop_value = self.get_value(pop_index)

        # remove field
        self._fields_l.pop(pop_index)

        return pop_value

    # ------------------------------------------------ GET -------------------------------------------------------------
    def get_field_index(self, field_index_or_name):
        """
        Returns field index (>=0).
        """
        if isinstance(field_index_or_name, int):
            field_index_or_name = (field_index_or_name if field_index_or_name >= 0 else
                                   self.fields_nb + field_index_or_name)
        return self._descriptor.get_field_index(field_index_or_name)

    def get_raw_value(self, field_index_or_name):
        field_index = self.get_field_index(field_index_or_name)
        return self._fields_l[field_index][self._RAW_VALUE]

    @cached
    def get_value(self, field_index_or_name):
        # parsed value and/or object
        index = self.get_field_index(field_index_or_name)
        raw_value = self._fields_l[index][self._RAW_VALUE]
        fieldd = self._descriptor.get_field_descriptor(index)
        if fieldd.detailed_type in ("integer", "real", "alpha", "choice", "node", "reference", "external-list"):
            value, pointed_index = fieldd.basic_parse(raw_value), None
        elif fieldd.detailed_type == "object-list":
            value, pointed_index = self._idf_manager.get_pointed_link(self._ref, index, raw_value)
        else:
            raise NotImplementedError("Unknown field type : '%s'." % fieldd.detailed_type)
        return value

    def get_field_comment(self, field_index_or_name):
        field_index = self.get_field_index(field_index_or_name)
        comment = self._fields_l[field_index][self._COMMENT]
        return "" if comment is None else comment

    def get_head_comment(self):
        return "" if self._head_comment is None else self._head_comment

    def get_tail_comment(self):
        return "" if self._tail_comment is None else self._tail_comment

    @cached
    def get_pointing_links_l(self, field_index_or_name=None):
        index_l = (range(len(self._fields_l)) if field_index_or_name is None
                   else [self.get_field_index(field_index_or_name)])

        links_l = []
        for i in index_l:
            fieldd = self._descriptor.get_field_descriptor(i)
            if fieldd.detailed_type != "reference":
                continue
            links_l.extend(self.idf_manager.get_pointing_links_l(self._ref, i, self.get_raw_value(i)))

        return links_l

    @property
    @cached
    def pointing_objects(self):
        return QuerySet([pointing_object for pointing_object, pointing_index in self.get_pointing_links_l()])

    # def get_pointed_links_l(self, field_index_or_name=None):
    #     """
    #     not used, not tested
    #     """
    #     index_l = (range(len(self._fields_l)) if field_index_or_name is None
    #                else [self.get_field_index(field_index_or_name)])
    #     links_l = []
    #     for i in index_l:
    #         value = self._fields_l[i][self._VALUE]
    #         if isinstance(value, IDFObject):
    #             links_l.append((value, self._fields_l[i][self._POINTED_INDEX]))
    #
    #     return links_l

    @cached
    def get_pointed_objects(self, field_index_or_name=None):
        """
        not used, not tested
        """
        index_l = (range(len(self._fields_l)) if field_index_or_name is None
                   else [self.get_field_index(field_index_or_name)])

        objects = []
        for i in index_l:
            value = self.get_value(i)
            if isinstance(value, IDFObject):
                objects.append(value)

        return objects

    # ------------------------------------------------ SET -------------------------------------------------------------
    @clear_cache
    def set_value(self, field_index_or_name, raw_value_or_value, raise_if_pointed=False):
        field_index = self.get_field_index(field_index_or_name)
        fieldd = self._descriptor.get_field_descriptor(field_index)

        if fieldd.detailed_type in ("integer", "real", "alpha", "choice", "node"):  # basic type
            # store and parse
            raw_value = "" if raw_value_or_value is None else str(raw_value_or_value).strip()
            self._fields_l[field_index][self._RAW_VALUE] = raw_value
            # self._parse_field(field_index)

        elif fieldd.detailed_type == "reference":
            if raise_if_pointed:
                if len(self.get_pointing_links_l(field_index)) > 0:
                    raise IsPointedError("Set field is already pointed by another object. First remove this object, "
                                         "or disable 'raise_if_pointed' argument.")
            # remove all pointing
            pointing_links_l = self.get_pointing_links_l(field_index)
            for pointing_object, pointing_index in pointing_links_l:
                pointing_object._.set_value(pointing_index, None)
            # store and parse
            raw_value = "" if raw_value_or_value is None else str(raw_value_or_value).strip()
            self._fields_l[field_index][self._RAW_VALUE] = raw_value
            # self._parse_field(field_index)
            # re-set all pointing
            for pointing_object, pointing_index in pointing_links_l:
                pointing_object._.set_value(pointing_index, self._idf_object)

        elif fieldd.detailed_type == "object-list":  # detailed type
            # convert to object if necessary
            if raw_value_or_value is None:
                self._fields_l[field_index][self._RAW_VALUE] = ""
            else:
                if isinstance(raw_value_or_value, str):
                    try:
                        value = self._idf_manager.add_object(raw_value_or_value)
                    except BrokenIDFError as e:
                        raise e
                    except Exception as e:
                        raise IDFError("Error while parsing string to create new object. Give object if "
                                       "exists or correct idf string.\n\n%s" % e)

                elif isinstance(raw_value_or_value, IDFObject):
                    value = raw_value_or_value
                else:
                    raise IDFError("Wrong value descriptor: '%s' (instead of IDFObject)." % type(raw_value_or_value))

                # check if correct idf
                if not value._.idf_manager is self._idf_manager:
                    raise IDFError("Given object does not belong to correct idf: '%s' instead of '%s." %
                                   (value._.idf_manager.path, self._idf_manager.path))

                # check that new object ref can be set, and find pointed index
                pointed_index = None
                for link_name in fieldd.get_tag("object-list"):
                    # link: (object_ref, index)
                    if pointed_index is not None:
                        break
                    for object_descriptor, object_index in self._idf_manager.idd.pointed_links(link_name):
                        if ((value._.ref.lower() == object_descriptor.ref.lower()) and
                                (value._.get_value(object_index) is not None)):
                            # ok, we fond an accepted combination
                            pointed_index = object_index
                            break
                if pointed_index is None:
                    raise IDFError("Wrong value ref: '%s' for field '%i' of object descriptor ref '%s'. "
                                   "Can't set object." % (value._.ref, field_index, self._ref))
                # get raw value
                raw_value = value._.get_raw_value(pointed_index)

                # now we checked everything was ok, we remove old field (so pointed object unlinks correctly)
                self._fields_l[field_index][self._RAW_VALUE] = ""

                # store and parse
                self._fields_l[field_index][self._RAW_VALUE] = raw_value
        else:
            raise IDFError("Unknown detailed type: '%s'." % fieldd.detailed_type)

        # remove if last field and emptied
        # if (len(self._fields_l) == (field_index+1)) and self._fields_l[-1][self._RAW_VALUE] == "":
        #     self._fields_l.pop()

    @clear_cache
    def replace_values(self, new_object_str):
        """
        Purpose: keep old pointed links
        """
        # create object (but it will not be linked to idf)
        objects_l, comments = self._idf_manager.parse(io.StringIO(new_object_str))  # comments not used
        if len(objects_l) != 1:
            raise IDFError("Wrong number of objects created: %i" % len(objects_l))
        new_object = objects_l[0]

        if self.ref != new_object._.ref:
            raise IDFError("New object (%s) does not have same reference as new object (%s). Can't replace." %
                           (self.ref, new_object._.ref))

        # replace fields using raw_values, one by one
        old_nb, new_nb = self.fields_nb, new_object._.fields_nb

        for i in range(max(old_nb, new_nb)):
            fieldd = self._descriptor.get_field_descriptor(i)

            if fieldd.detailed_type in ("reference", "object-list"):
                continue  # we do not modifiy links

            if (i < old_nb) and (i < new_nb):
                self.set_value(i, new_object._.get_raw_value(i))
            elif i < old_nb:
                self.set_value(i, None)
            else:
                self.add_field(new_object._.get_raw_value(i), new_object._.get_field_comment(i))

        # remove all last values
        self._fields_l = self._fields_l[:new_nb]

    @clear_cache
    def set_field_comment(self, field_index_or_name, comment):
        field_index = self.get_field_index(field_index_or_name)
        comment = None if comment.strip() == "" else str(comment).replace("\n", " ").strip()
        self._fields_l[field_index][self._COMMENT] = comment

    @clear_cache
    def set_head_comment(self, comment):
        """
        All line return will be replaced by a blank.
        """
        comment = None if comment.strip() == "" else str(comment).replace("\n", " ").strip()
        self._head_comment = comment

    @clear_cache
    def set_tail_comment(self, comment):
        comment = None if comment.strip() == "" else str(comment).strip()
        self._tail_comment = comment

    # ------------------------------------------------ COMMUNICATE -----------------------------------------------------
    def to_str(self, style="idf", idf_style=None):
        if style == "idf":
            if idf_style is None:
                idf_style = style_library[CONF.default_write_style]
            if isinstance(idf_style, IDFStyle):
                idf_style = idf_style
            elif isinstance(idf_style, str):
                if idf_style in style_library.keys():
                    idf_style = style_library[style]
                else:
                    idf_style = style_library[CONF.default_write_style]
            else:
                idf_style = style_library[CONF.default_write_style]
            # object descriptor ref
            content = "%s" % self._descriptor.ref + ("," if self.fields_nb != 0 else ";")
            spaces_nb = self._COMMENT_COLUMN_START - len(content)
            if spaces_nb < 0:
                spaces_nb = self._TAB_LEN

            s = ""

            # Tail comment if the type is before the object
            if idf_style.tail_type == "before":
                if self._tail_comment:
                    s += "\n"
                    for line in self._tail_comment.strip().split("\n"):
                        s += idf_style.get_tail_object_comment(line)

            # MANAGE HEAD COMMENT
            if self._head_comment:
                comment = "%s" % (" " * spaces_nb) + idf_style.get_object_comment(
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
                    comment = (" " * spaces_nb) + idf_style.get_object_comment(
                        f_comment,
                        line_jump=False
                    )
                else:
                    comment = ""
                s += content + comment + "\n"

            # Tail comment if the type is after the object
            if idf_style.tail_type == "after":
                if self._tail_comment:
                    s += "\n"
                    for line in self._tail_comment.strip().split("\n"):
                        s += idf_style.get_tail_object_comment(line)

        elif style == "console":
            s = "%s\n%s%s\n" % ("-" * self._ROWS_NB, str(self.to_str(style="idf")), "-" * self._ROWS_NB)
        else:
            raise IDFError("Unknown style: '%s'." % style)

        return s

    def info(self, detailed=False):
        """
        Returns a string with all available fields of object (information provided by the idd).
        Arguments
        ---------
            detailed: include all field tags information
        """
        msg = "%s\n%s\n%s" % ("-"*len(self._ref), self._ref, "-"*len(self._ref))
        for i, fd in enumerate(self._descriptor.field_descriptors_l):
            msg += "\n%i: %s" % (i, fd.name)
            if detailed:
                for tag in fd.tags:
                    msg += "\n\t* %s: %s" % (tag, fd.get_tag(tag))
        return msg


# ----------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------- IDF ----------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- idf manager  ---------------------------------------------------------
class VoidSimulation:
    def __getattr__(self, item):
        raise IDFError("Idf is not attached to a simulation, '%s' enhancement is not available." % item)


class IDFManager(Cached):
    idf_object_manager_cls = IDFObjectManager  # for subclassing

    # ----------------------------------------------- INITIALIZE -------------------------------------------------------
    def __init__(self, idf, path_or_content, idd_or_path=None, encoding=None, style=None):
        self._activate_cache()
        self._idf = idf
        self._idd = IDD.get_idd(idd_or_path, encoding=encoding)
        self._encoding = CONF.encoding if encoding is None else encoding
        self._constructing_mode = False

        # simulation
        self._simulation = VoidSimulation()  # must be before parsing

        # get string buffer and store path (for info)
        buffer, path = get_string_buffer(path_or_content, "idf", self._encoding)
        self._path = path_or_content

        # raw parse and parse
        with buffer as f:
            try:
                self._objects_l, self._head_comments = self.parse(f, style)
            except Exception as e:
                raise IDFError("Error while parsing idf. First check that given file exists "
                               "(if not, given path will have been considered as an idf content.\n%s" % e)

    # ----------------------------------------------- EXPOSE -----------------------------------------------------------
    @staticmethod
    def copyright_comment():
        return get_copyright_comment()

    @property
    def objects_l(self):
        return self._objects_l

    @property
    def idd(self):
        return self._idd

    @property
    def simulation(self):
        return self._simulation

    @property
    def idf(self):
        return self._idf

    # --------------------------------------------- CONSTRUCT ----------------------------------------------------------
    @property
    @contextmanager
    def under_construction(self):
        """
        Allows the user to deactivate new reference checks while adding objects. The whole idf is checked afterwards.
        This allows to construct idfs more efficiently.
        """
        self._constructing_mode = True
        yield
        self.check_duplicate_references()
        self._constructing_mode = False

    def parse(self, file_like, style=None):
        """
        Objects are created from string. They are not attached to idf manager yet.
        in idf: header comment, chapter comments, objects
        in object: head comment, field comments, tail comment
        """
        if style is None:
            style = style_library[CONF.default_read_style]
        if isinstance(style, IDFStyle):
            style = style
        elif isinstance(style, str):
            if style in style_library.keys():
                style = style_library[style]
            else:
                style = style_library[CONF.default_read_style]
        else:
            style = style_library[CONF.default_read_style]

        objects_l, head_comments = [], ""
        idf_object_manager = None
        make_new_object = True

        tail_comments = ""

        for i, raw_line in enumerate(file_like):
            # GET LINE CONTENT AND COMMENT
            split_line = raw_line.split("!")

            # No "!" in the raw_line
            if len(split_line) == 1:
                # This is an empty line
                if len(split_line[0].strip()) == 0:
                    content, comment = None, None
                # This is an object line with no comments
                else:
                    content, comment = split_line[0].strip(), None
            # There is at least one "!" in the raw_line
            else:
                # This is a comment line
                if len(split_line[0].strip()) == 0:
                    content, comment = None, "!".join(split_line[1:])
                # This is an object line with a comment
                else:
                    content, comment = split_line[0].strip(), "!".join(split_line[1:])

            # SKIP CURRENT LINE IF VOID
            if (content, comment) == (None, None):
                continue

            # NO CONTENT
            if not content:
                if idf_object_manager is None:  # head idf comment
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
                    elif comment[:len(style.tail_object_key)] == style.tail_object_key:
                        comment = comment[len(style.tail_object_key):].strip().replace("\n", "")
                        if style.tail_type == "before":
                            tail_comments += comment + "\n"
                        elif style.tail_type == "after":
                            idf_object_manager.add_tail_comment(comment)

                continue

            # CONTENT
            # check if object end and prepare
            object_end = content[-1] == ";"
            content = content[:-1]  # we tear comma or semi-colon
            content_l = [text.strip() for text in content.split(",")]

            if comment:
                if style is None:
                    comment = comment.strip().replace("\n", "")
                elif comment[:len(style.object_key)] == style.object_key:
                    comment = comment[len(style.object_key):].strip().replace("\n", "")
                else:
                    comment = None

            field_comment = comment
            # object creation if needed
            if make_new_object:
                if not object_end and len(content_l) > 1:
                    head_comment = None
                    field_comment = comment
                else:
                    head_comment = comment
                    field_comment = None

                idf_object_manager = self.idf_object_manager_cls(content_l[0].strip(), self, head_comment=head_comment)
                objects_l.append(idf_object_manager.idf_object)
                # prepare in case fields on the same line
                content_l = content_l[1:]
                make_new_object = False

            # fields
            for value_s in content_l:
                idf_object_manager.add_field(value_s, comment=field_comment)

            # signal that new object must be created
            if object_end:
                if style:
                    if style.tail_type == "before":
                        idf_object_manager.add_tail_comment(tail_comments)
                        tail_comments = ""
                make_new_object = True

        return objects_l, head_comments

    # ----------------------------------------------- LINKS ------------------------------------------------------------
    @cached
    def get_pointed_link(self, pointing_ref, pointing_index, pointing_raw_value):
        # get field descriptor
        fieldd = self._idd.get_object_descriptor(pointing_ref).get_field_descriptor(pointing_index)
        # check if object-list
        if fieldd.detailed_type != "object-list":
            raise IDFError("Only 'object-list' fields can point on an object. Wrong field given. Ref: '%s', "
                           "index: '%i'." % (pointing_ref, pointing_index))
        # check if an object is pointed
        if pointing_raw_value == "":  # no object pointed
            return None, None
        # iter through link possibilities and return if found
        link_names_l = fieldd.get_tag("object-list")
        for link_name in link_names_l:
            for od, field_index in self._idd.pointed_links(link_name):
                for idf_object in self.filter_by_ref(od.ref):
                    if idf_object._.get_raw_value(field_index) == pointing_raw_value:
                        return idf_object, field_index
        raise IDFError("Link not found. Field 'object-list' tag values: %s, field value : '%s'" %
                       (str(link_names_l), pointing_raw_value))

    @cached
    def get_pointing_links_l(self, pointed_ref, pointed_index, pointed_raw_value):
        # get field descriptor
        fieldd = self.idd.get_object_descriptor(pointed_ref).get_field_descriptor(pointed_index)
        # check if reference
        if fieldd.detailed_type != "reference":
            raise IDFError("Only 'reference' fields can be pointed by an object. Wrong field given. Ref: '%s', "
                           "index: '%i'." % (pointed_ref, pointed_index))
        # check if an object can be pointing
        if pointed_raw_value == "":
            return []
        # fetch links
        links_l = []
        for link_name in fieldd.get_tag("reference"):
            for object_descriptor, pointing_index in self.idd.pointing_links(link_name):
                for idf_object in self.filter_by_ref(object_descriptor.ref):
                    if pointing_index >= idf_object._.fields_nb:
                        continue
                    if idf_object._.get_raw_value(pointing_index) == pointed_raw_value:
                        links_l.append([idf_object, pointing_index])
        return links_l

    def check_new_reference(self, new_object_ref, new_object_index, reference):
        if reference == "":
            return None
        # check that there is no duplicate reference (i.e. none of the links which will point to this field already
        # points to another field with the same reference)
        links_l = self.get_pointing_links_l(new_object_ref, new_object_index, reference)
        if len(links_l) != 0:
            raise BrokenIDFError(
                "New object has same reference at index '%s' as other object of same link name. "
                "Other object ref: '%s', index: '%s'. The value at that field must be changed." %
                (new_object_index, links_l[0][0]._.ref, links_l[0][1])
            )

    def check_duplicate_references(self):
        # we create a dict containing for each link_name a set of references to check that they are unique
        ref_d = dict()
        for object in self.objects_l:
            # check reference uniqueness
            object_descriptor = self._idd.get_object_descriptor(object._.ref)
            for i in range(object._.fields_nb):
                fieldd = object_descriptor.get_field_descriptor(i)
                if fieldd.detailed_type == "reference":
                    reference = object._.get_raw_value(i)
                    for link_name in fieldd.get_tag("reference"):
                        # for each link name add the reference to the set to check for uniqueness
                        if link_name not in ref_d:
                            ref_d[link_name] = set()
                        if reference in ref_d[link_name]:
                            raise BrokenIDFError(
                                "Reference duplicate for link name: {}\n".format(link_name) +
                                "Reference: {}\n".format(reference) +
                                "Detected while checking object ref: {}\n".format(object._.ref) +
                                "Field: {}".format(i)
                            )
                        ref_d[link_name].add(reference)

    # ------------------------------------------ MANAGE OBJECTS --------------------------------------------------------
    def has_object(self, idf_object):
        return idf_object in self._objects_l

    @clear_cache
    def add_object(self, new_str, position=None):
        """
        From str
        """
        # create object
        objects_l, comments_l = self.parse(io.StringIO(new_str))  # comments not used (only for global idf parse)
        if len(objects_l) != 1:
            raise IDFError("Wrong number of objects created: %i" % len(objects_l))
        new_object = objects_l[0]
        return self.add_object_from_parsed(new_object._, position=position)

    @clear_cache
    def add_object_from_parsed(self, raw_parsed_object_manager, position=None):
        """checks references uniqueness"""
        new_object = raw_parsed_object_manager.idf_object  # change name since no more raw parsed

        # check reference uniqueness
        object_descriptor = self._idd.get_object_descriptor(new_object._.ref)
        for i in range(new_object._.fields_nb):
            fieldd = object_descriptor.get_field_descriptor(i)
            if fieldd.detailed_type == "reference" and not self._constructing_mode:
                self.check_new_reference(object_descriptor.ref, i, new_object._.get_raw_value(i))

        # add object
        if position is None:
            self._objects_l.append(new_object)
        else:
            self._objects_l.insert(position, new_object)

        # return new object
        return new_object

    @clear_cache
    def remove_object(self, idf_object, raise_if_pointed=True):
        """
        Arguments
        ---------
        raise_if_pointed: raises Exception if is pointed by other objects.
            Else, sets all pointing object fields to None.
        """
        # check if object is pointed, if asked
        pointing_links_l = idf_object._.get_pointing_links_l()
        if raise_if_pointed and len(pointing_links_l) > 0:
            raise IsPointedError("Can't remove object if other objects are pointing to it and 'check' is "
                                 "True. Pointing objects: '%s'" % [o for (o, i) in pointing_links_l])

        # remove from pointing
        for pointing_object, pointing_index in pointing_links_l:
            pointing_object._.remove_values_that_point(idf_object)

        # remove pointed
        idf_object._.remove_values_that_point()

        # delete obsolete attributes
        idf_object._.neutralize()

        # remove from idf
        index = self._objects_l.index(idf_object)
        del self._objects_l[index]

        return index

    @cached
    def filter_by_ref(self, ref=None):
        if ref is None:
            return QuerySet(self.objects_l)
        return QuerySet(self._objects_l)(ref)

    # ------------------------------------------ MANAGE COMMENTS -------------------------------------------------------
    def get_comment(self):
        return self._head_comments

    @clear_cache
    def set_comment(self, value):
        self._head_comments = str(value).strip()

    # ------------------------------------------------ COMMUNICATE -----------------------------------------------------
    def info(self, sort_by_group=False, detailed=False):
        """
        Indicates all objects references contained in current idf.
        Arguments
        ---------
        sort_by_group: will sort object descriptors by group
        detailed: will give all object descriptors' associated tags
        Returns
        -------
        a text describing the information on object contained in idd file
        """
        # ods: object descriptors
        def _get_ods_info(_ods, _line_start=""):
            _msg = ""
            for _od in sorted(_ods, key=lambda x: x.ref):
                _msg += "\n%s%s" % (_line_start, _od.ref)
                if detailed:
                    for _tag in _od.tags:
                        _msg += "\n%s\t* %s: %s" % (_line_start, _tag, _od.get_tag(_tag))
            return _msg

        ods_refs_set = set([idf_object.ref for idf_object in self._objects_l])
        name = "IDF: '%s'" % self._path
        msg = "%s\n%s\n%s" % ("-"*len(name), name, "-"*len(name))
        if sort_by_group:
            for group_name in self._idd.groups_l:
                ods_l = []
                for od in self._idd.get_object_descriptors_by_group(group_name):
                    if od.ref in ods_refs_set:
                        ods_l.append(od)
                if len(ods_l) > 0:
                    msg += "\nGroup - %s" % group_name
                    msg += _get_ods_info(ods_l, _line_start="\t")
        else:
            msg += _get_ods_info([self._idd.get_object_descriptor(od_ref) for od_ref in ods_refs_set])

        return msg

    def to_str(self, style=None, add_copyright=True, clean=False):
        if style is None:
            style = style_library[CONF.default_write_style]
        if isinstance(style, IDFStyle):
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

        if clean:
            object_ref_set = set()
            for obj in self._objects_l:
                object_ref_set.add(obj.ref)

            for ref in sorted(object_ref_set):
                content += "\n" + style.get_chapter_title(ref)
                for idf_object in self.filter_by_ref(ref):
                    content += "\n%s" % idf_object._.to_str(style="idf", idf_style=style)

        else:
            for idf_object in self._objects_l:
                content += "\n%s" % idf_object._.to_str(style="idf", idf_style=style)

        return content

    def save_as(self, file_or_path, style=None, add_copyright=True, clean=False):
        is_path = isinstance(file_or_path, str)
        f = open(file_or_path, "w", encoding=self._encoding) if is_path else file_or_path
        f.write(self.to_str(style=style, add_copyright=add_copyright, clean=clean))
        if is_path:
            f.close()

    def copy(self, add_copyright=True):
        content = self.to_str(add_copyright=add_copyright)
        return self.idf.__class__(content, self.idd, encoding=self._encoding)


# ------------------------------------------------- idf ----------------------------------------------------------------
class IDF:
    """
    IDF is allowed to access private keys/methods of IDFObject.
    """
    idf_manager_cls = IDFManager  # for subclassing

    @classmethod
    def get_idf(cls, idf_or_path, encoding=None):
        """
        Arguments
        ---------
        idf_or_path: idf object or idf file path
        Returns
        -------
        IDF object
        """
        if isinstance(idf_or_path, str):
            return cls(idf_or_path, encoding=encoding)
        elif isinstance(idf_or_path, cls):
            return idf_or_path
        raise IDFError("'idf_or_path' must be a path or an IDF. Given object: '%s', type: '%s'." %
                       (idf_or_path, type(idf_or_path)))

    def __init__(self, path_or_content, idd_or_path=None, encoding=None, style=None):
        """
        Arguments
        ---------
        path_or_content: idf path, content str, content bts or file_like. If path, must end by .idf.
        idd_or_path: IDD object or idd path. If None, default will be chosen (most recent EPlus version installed on
            computer)
        """
        self._ = self.idf_manager_cls(
            self,
            path_or_content,
            idd_or_path=idd_or_path,
            encoding=encoding,
            style=style
        )

    def __call__(self, object_descriptor_ref=None):
        """returns all objects of given object descriptor"""
        return self._.filter_by_ref(object_descriptor_ref)

    def to_str(self, add_copyright=True):
        return self._.to_str(add_copyright=add_copyright)

    def save_as(self, file_or_path, style=None, clean=False):
        self._.save_as(file_or_path, style=style, clean=clean)

    def copy(self, add_copyright=True):
        return self._.copy(add_copyright=add_copyright)

    def remove_object(self, object_to_remove, raise_if_pointed=True):
        """
        Removes object from idf.
        Arguments
        ---------
        old: object to remove
        check: check if links have been broken. If check is True and broken links are detected, will raise an IDFError.
            (nodes or branches checking has not been implemented)
        """
        return self._.remove_object(object_to_remove, raise_if_pointed=raise_if_pointed)

    def add_object(self, new_str, position=None):
        """
        Adds new object to the idf, at required position.
        Arguments
        ---------
        new_or_str: new object (or string describing new object) that will be added to idf
        position: if None, will be added at the end, else will be added at asked position
            (using 'insert' python builtin function for lists)
        check: check if pointed objects of new object exists. If check is True and a non existing link is detected, will
            raise an IDFError
        """
        return self._.add_object(new_str, position=position)

    def info(self, sort_by_group=False, detailed=False):
        """
        Arguments
        ---------
        sort_by_group: will sort object descriptors by group
        detailed: will give all object descriptors' associated tags
        Returns
        -------
        a text describing the information on object contained in idd file
        """
        return self._.info(sort_by_group=sort_by_group, detailed=detailed)

    @property
    def comment(self):
        return self._.get_comment()

    @comment.setter
    def comment(self, value):
        self._.set_comment(value)

    # todo: remove this method at the next major update
    def activate_cache(self):
        warnings.warn(
            "activate_cache is deprecated and will be removed: the cache is now managed automatically",
            category=DeprecationWarning
        )

    # todo: remove this method at the next major update
    def deactivate_cache(self):
        warnings.warn(
            "deactivate_cache is deprecated and will be removed: the cache is now managed automatically",
            category=DeprecationWarning
        )

    def clear_cache(self):
        self._.clear_cache()

    @property
    @contextmanager
    def under_construction(self):
        with self._.under_construction:
            yield


# ----------------------------------------------------------------------------------------------------------------------
# --------------------------------------------- QuerySet ---------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
class QuerySet:
    """Contains object, and enables filtering or other operations. Is allowed to access object._."""
    def __init__(self, objects_l):
        self._objects_l = objects_l

    @property
    def objects_l(self):
        return self._objects_l

    def filter(self, field_index_or_name, field_value, condition="="):
        """
        Filter all objects who's field value matches field_value according to given condition.
        Arguments
        ---------
        field_index_or_name: field index or name. Can access children with tuple or list.
        field_value_or_values: value on which to be matched.
        condition: "=" (equality)
        condition: 'in' (include in string field)
        Returns
        -------
        QuerySet containing filtered objects.
        """
        if condition not in ("=", 'in'):
            raise IDFError("Unknown condition: '%s'." % condition)

        search_tuple = (field_index_or_name,) if isinstance(field_index_or_name, str) else field_index_or_name

        result_l = []
        for o in self._objects_l:
            current_value = o
            for level in search_tuple:
                current_value = current_value._.get_value(level)
            if condition == '=':
                if isinstance(current_value, str) and isinstance(field_value, str):
                    if current_value.lower() == field_value.lower():
                        result_l.append(o)
                elif not isinstance(current_value, type(field_value)):
                    raise IDFError("filter element type %s is not correct" % type(field_value))
                else:
                    if current_value == field_value:
                        result_l.append(o)
            elif condition == 'in':
                if not isinstance(current_value, str):
                    raise IDFError("condition 'in' can not been performed on field_value  of type %s." % type(field_value))
                if field_value.lower() in current_value.lower():
                    result_l.append(o)
            else:
                raise IDFError("unknown condition : '%s'" % condition)

        return QuerySet(result_l)

    @property
    def one(self):
        """
        Checks that query set only contains one object and returns it.
        """
        if len(self._objects_l) == 0:
            raise ObjectDoesNotExist("Query set contains no value.")
        if len(self._objects_l) > 1:
            raise MultipleObjectsReturned("Query set contains more than one value.")
        return self[0]

    def __getitem__(self, item):
        return self._objects_l[item]

    def __iter__(self):
        return iter(self._objects_l)

    def __str__(self):
        return "<QuerySet: %s>" % str(self._objects_l)

    def __call__(self, object_descriptor_ref=None):
        """Returns all objects having given object descriptor ref (not case sensitive)."""
        if object_descriptor_ref is None:  # return a copy
            return QuerySet([o for o in self._objects_l])
        return QuerySet([o for o in self._objects_l if o._.ref.lower() == object_descriptor_ref.lower()])

    @clear_cache
    def __add__(self, other):
        """
        Add new query set to query set (only new objects will be added).
        """
        self_set = set(self._objects_l)
        other_set = set(other.objects_l)
        intersect_set = self_set.intersection(other_set)
        new_objects_l = []
        new_objects_l.extend(self._objects_l)
        for idf_object in other.objects_l:
            if idf_object not in intersect_set:
                new_objects_l.append(idf_object)
        return QuerySet(new_objects_l)

    def __len__(self):
        return len(self._objects_l)




