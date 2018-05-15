from contextlib import contextmanager
import io

from oplus import CONF
from oplus.idd.idd import Idd
from oplus.util import get_copyright_comment, get_string_buffer
from .cache import Cached, cached, clear_cache
from .style import IdfStyle, style_library
from .record_manager import RecordManager
from .exceptions import BrokenIdfError, IsPointedError
from .queryset import QuerySet


class IdfManager(Cached):
    record_manager_cls = RecordManager  # for subclassing

    # ----------------------------------------------- INITIALIZE -------------------------------------------------------
    def __init__(self, idf, path_or_content, idd_or_path=None, encoding=None, style=None):
        self.activate_cache()
        self._idf = idf
        self._idd = Idd.get_idd(idd_or_path, encoding=encoding)
        self._encoding = CONF.encoding if encoding is None else encoding
        self._constructing_mode = False

        # get string buffer and store path (for info)
        buffer, path = get_string_buffer(path_or_content, "idf", self._encoding)
        self._path = path_or_content

        # raw parse and parse
        with buffer as f:
            self._objects_l, self._head_comments = self.parse(f, style)

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
        if isinstance(style, IdfStyle):
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

                idf_object_manager = self.record_manager_cls(content_l[0].strip(), self, head_comment=head_comment)
                objects_l.append(idf_object_manager.record)
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
        fieldd = self._idd.get_record_descriptor(pointing_ref).get_field_descriptor(pointing_index)
        # check if object-list
        assert fieldd.detailed_type == "object-list", \
            "Only 'object-list' fields can point on an object. " \
            f"Wrong field given. Ref: '{pointing_ref}', index: '{pointing_index}'."
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
        raise RuntimeError(
            f"Link not found. "
            f"Field 'object-list' tag values: {str(link_names_l)}, field value : '{pointing_raw_value}'"
        )

    @cached
    def get_pointing_links_l(self, pointed_ref, pointed_index, pointed_raw_value):
        # get field descriptor
        fieldd = self.idd.get_record_descriptor(pointed_ref).get_field_descriptor(pointed_index)
        # check if reference
        assert fieldd.detailed_type == "reference", \
            "Only 'reference' fields can be pointed by an object. Wrong field given. " \
            f"Ref: '{pointed_ref}', index: '{pointed_index}'."
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
            raise BrokenIdfError(
                "New object has same reference at index '%s' as other object of same link name. "
                "Other object ref: '%s', index: '%s'. The value at that field must be changed." %
                (new_object_index, links_l[0][0]._.ref, links_l[0][1])
            )

    def check_duplicate_references(self):
        # we create a dict containing for each link_name a set of references to check that they are unique
        ref_d = dict()
        for object in self.objects_l:
            # check reference uniqueness
            object_descriptor = self._idd.get_record_descriptor(object._.ref)
            for i in range(object._.fields_nb):
                fieldd = object_descriptor.get_field_descriptor(i)
                if fieldd.detailed_type == "reference":
                    reference = object._.get_raw_value(i)
                    for link_name in fieldd.get_tag("reference"):
                        # for each link name add the reference to the set to check for uniqueness
                        if link_name not in ref_d:
                            ref_d[link_name] = set()
                        if reference in ref_d[link_name]:
                            raise BrokenIdfError(
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
        assert len(objects_l) == 1, "Wrong number of objects created: %i" % len(objects_l)
        new_object = objects_l[0]
        return self.add_object_from_parsed(new_object._, position=position)

    @clear_cache
    def add_object_from_parsed(self, raw_parsed_object_manager, position=None):  # todo: change name and move to table
        """checks references uniqueness"""
        new_object = raw_parsed_object_manager.record  # change name since no more raw parsed

        # check reference uniqueness
        object_descriptor = self._idd.get_record_descriptor(new_object._.ref)
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
        name = "Idf: '%s'" % self._path
        msg = "%s\n%s\n%s" % ("-"*len(name), name, "-"*len(name))
        if sort_by_group:
            for group_name in self._idd.groups_l:
                ods_l = []
                for od in self._idd.get_record_descriptors_by_group(group_name):
                    if od.ref in ods_refs_set:
                        ods_l.append(od)
                if len(ods_l) > 0:
                    msg += "\nGroup - %s" % group_name
                    msg += _get_ods_info(ods_l, _line_start="\t")
        else:
            msg += _get_ods_info([self._idd.get_record_descriptor(od_ref) for od_ref in ods_refs_set])

        return msg

    def to_str(self, style=None, add_copyright=True, clean=False):
        # todo: change clean to sort, make default true, (and order table refs by idd order ?)
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

        if clean:
            # store objects str (before order)
            objects_l = []  # [(table_ref, obj_str), ...]
            for obj in self._objects_l:
                objects_l.append((obj.ref, "\n%s" % obj._.to_str(style="idf", idf_style=style)))

            # iter sorted list and add chapter titles
            current_ref = None

            for (obj_ref, obj_str) in sorted(objects_l):
                # write chapter title if needed
                if obj_ref != current_ref:
                    current_ref = obj_ref
                    content += "\n" + style.get_chapter_title(current_ref)

                # write object
                content += obj_str

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

