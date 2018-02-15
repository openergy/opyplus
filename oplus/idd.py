"""
IDD
---
Manages the EPlus idd file.

Definitions
-----------
object: EPlus object
field: EPlus object field
object descriptor: description of an object, given by the idd. An object descriptor has a unique ref (given by idd)
field descriptor: object descriptor field

pointing object (has tag 'object-list'): object that points towards another object
pointed object (has tag 'reference'): object being pointed by another object

"""

import os
import re
import logging

from oplus.configuration import CONF


class IDDError(Exception):
    pass


def get_idd_path():
    return os.path.join(CONF.eplus_base_dir_path, "Energy+.idd")


class FieldDescriptor:
    """
    No checks implemented (idf is considered as ok).
    """
    def __init__(self, field_basic_type, name=None):
        if field_basic_type not in ("A", "N"):
            raise IDDError("Unknown field type: '%s'." % field_basic_type)
        self.basic_type = field_basic_type  # A -> alphanumeric, N -> numeric
        self.name = name
        self._tags_d = {}

        self._detailed_type = None

    @property
    def tags(self):
        return sorted(self._tags_d)

    def add_tag(self, ref, value=None):
        if ref not in self._tags_d:
            self._tags_d[ref] = []
        if value is not None:
            self._tags_d[ref].append(value)

    def get_tag(self, ref):
        """
        Returns tag belonging to field descriptor. If 'note', will be string, else list of elements.
        """
        if ref == "note":  # memo is for object descriptors
            return " ".join(self._tags_d[ref])
        return self._tags_d[ref]

    def has_tag(self, ref):
        return ref in self._tags_d

    def basic_parse(self, value):
        """
        Parses raw value (string or None) to string, int, float or None.
        """
        # no value
        if (value is None) or (value == ""):
            return None

        # alphabetical
        if self.basic_type == "A":
            return str(value)

        # numeric
        if type(value) is str:
            if value.lower() in ("autocalculate", "autosize"):
                return value
            try:
                return int(value)
            except ValueError:
                return float(value)

        # in case has already been parsed
        elif type(value) in (int, float):
            return value

    @property
    def detailed_type(self):
        """
        Uses EPlus double approach of type ('type' tag, and/or 'key', 'object-list', 'external-list', 'reference' tags)
        to determine detailed type.
        Returns
        -------
        "integer", "real", "alpha", "choice", "reference", "object-list", "external_list", "node"
        """
        if self._detailed_type is None:
            if "reference" in self._tags_d:
                self._detailed_type = "reference"
            elif "type" in self._tags_d:
                self._detailed_type = self._tags_d["type"][0].lower()
            elif "key" in self._tags_d:
                self._detailed_type = "choice"
            elif "object-list" in self._tags_d:
                self._detailed_type = "object-list"
            elif "external-list" in self._tags_d:
                self._detailed_type = "external-list"
            elif self.basic_type == "A":
                self._detailed_type = "alpha"
            elif self.basic_type == "N":
                self._detailed_type = "real"
            else:
                raise IDDError("Can't find detailed type.")
        return self._detailed_type

    @staticmethod
    def name_to_formatted_name(name):
        """
        Returns formatted name of variable (lower case).
        """
        return name.lower()


class ObjectDescriptor:
    """
    Describes a EPlus object (see idd).
    """
    def __init__(self, ref, group_name=None):
        self.ref = ref
        self.group_name = group_name
        self._fieldds_l = []
        self._tags_d = {}

        # extensible management
        self._extensible_cycle_len = 0  # if 0: not extensible
        self._extensible_cycle_start = None  # will be filled first time asked

    @property
    def tags(self):
        return sorted(self._tags_d)

    @property
    def field_descriptors_l(self):
        return self._fieldds_l

    def get_tag(self, ref):
        """
        Returns tag belonging to object descriptor. If 'memo', will be string, else list of elements.
        """
        if ref == "memo":  # note if for field descriptors
            return " ".join(self._tags_d[ref])
        return self._tags_d[ref]

    def add_tag(self, ref, value=None):
        if value is None:
            return None

        if not ref in self._tags_d:
            self._tags_d[ref] = []
        self._tags_d[ref].append(value)

        # manage extensible
        if "extensible" in ref:
            self._extensible_cycle_len = int(ref.split(":")[1])

    def add_field_descriptor(self, field):
        """
        Adds a new field descriptor.
        """
        self._fieldds_l.append(field)

    def get_field_descriptor(self, index_or_name):
        """
        Returns
        -------
        asked field descriptor.
        """
        if self.ref in ("Schedule:Compact", "BranchList"):
            if self.extensible[0] is not None:
                self._fieldds_l.extend([ self._fieldds_l[self.extensible[1]+i] for i in range(self.extensible[0])
                                         for x in range(200)])

        index = self.get_field_index(index_or_name)

        if index >= len(self._fieldds_l) and (self._extensible_cycle_len != 0):# extensible object, find modulo
            index = self._extensible_cycle_len + ((index - self._extensible_cycle_start) % self._extensible_cycle_len)

        return self._fieldds_l[index]

    def get_field_index(self, index_or_name):
        """
        if index, must be >=0
        """
        # if index
        if type(index_or_name) is int:
            if index_or_name >= len(self._fieldds_l) and (self._extensible_cycle_len == 0):
                raise IDDError("Index out of range : %i." % index_or_name)
            return index_or_name
        # if name (extensible can not be used here)
        formatted_name = FieldDescriptor.name_to_formatted_name(index_or_name)
        for i, cur_field in enumerate(self._fieldds_l):
            cur_formatted_name = FieldDescriptor.name_to_formatted_name(cur_field.name)
            if cur_formatted_name == formatted_name:
                return i
        raise IDDError("No field of '%s' is named '%s'." % (self.ref, index_or_name))

    @property
    def formatted_ref(self):
        return self.ref.replace(":", "_")

    @property
    def extensible(self):
        """
        Returns cycle_len, cycle_start
        """
        if self._extensible_cycle_len == 0:
            return None, None
        if self._extensible_cycle_start is None:
            for i, fieldd in enumerate(self._fieldds_l):
                if fieldd.has_tag("begin-extensible"):
                    break
            else:
                raise IDDError("begin-extensible tag not found.")
            self._extensible_cycle_start = i
        return self._extensible_cycle_len, self._extensible_cycle_start

class IDD:
    @classmethod
    def get_idd(cls, idd_or_path, logger_name=None, encoding=None):
        if idd_or_path is None:
            return cls()
        if isinstance(idd_or_path, str):
            return cls(path=idd_or_path, logger_name=logger_name, encoding=encoding)
        elif isinstance(idd_or_path, cls):
            return idd_or_path
        raise IDDError("'idd_or_path' must be a path or an IDD. Given object: '%s', type: '%s'." %
                       (idd_or_path, type(idd_or_path)))

    def __init__(self, path=None, logger_name=None, encoding=None):
        if (path is not None) and not os.path.exists(path):
            raise IDDError("No file at given path: '%s'." % path)
        self.path = get_idd_path() if path is None else path
        self._logger_name = logger_name
        self._encoding = encoding
        # od: object descriptor, linkd: link descriptor
        self._ods_d = {}  # object descriptors {lower_object_descriptor_ref: od, ...}
        self._pointed_od_linkds_d = {}  # linkd: link descriptor {link_name: [(od, field_index), ...], ...}
        self._pointing_od_linkds_d = {}  # {link_name: [(od, field_index), ...], ...}
        self._groups_d = {}  # {group name: [od, od, ...]}

        self._parse()
        self._link()

    def pointed_links(self, link_name):
        """
        Returns all the possible links named 'link_name' to pointed objects. A link is a combination of an object
        descriptor and an index. This corresponds to fields having a 'reference' tag.

        Returns
        -------
        list of links: [(object_descriptor_ref, index), ...]
        """
        if not link_name in self._pointed_od_linkds_d:
            logger = logging.getLogger(default_logger_name if self._logger_name is None else self._logger_name)
            logger.info("Idd useless ref -> '%s' ref is defined, but no object-list pointing (idd problem, "
                        "nothing to do)." % link_name)
            return []
        return self._pointed_od_linkds_d[link_name]

    def pointing_links(self, link_name):
        """
        Returns all the possible links named 'link_name' to pointing objects. A link is a combination of an object
        descriptor and an index. This corresponds to a field having an 'object-list' tag.

        Returns
        -------
        list of links: [(object_descriptor_ref, index), ...]
        """
        if not link_name in self._pointing_od_linkds_d:
            logger = logging.getLogger(default_logger_name if self._logger_name is None else self._logger_name)
            logger.debug("No pointing links ('object-list') with name '%s'. This may be an idd bug, or a wrong "
                         "link_name may have been provided." % link_name)
            return []
        return self._pointing_od_linkds_d[link_name]

    @property
    def groups_l(self):
        """
        All group names.
        """
        return sorted(self._groups_d)

    def _parse(self):
        """ Parses idd file."""
        group_name, od, fieldd = None, None, None
        with open(self.path, "r", encoding=CONF.encoding if self._encoding is None else self._encoding) as f:
            for i, raw_line in enumerate(f):
                line = raw_line.split("!")[0]  # we tear comment

                # blank line
                if re.search(r"^\s*$", line) is not None:
                    continue

                # group comment (must be before comments)
                match = re.search(r"^\\group (.+)$", line)
                if match is not None:
                    group_name = match.group(1).strip()
                    self._groups_d[group_name] = []
                    # re-initialize
                    od, fieldd = None, None
                    continue

                # tag
                match = re.search(r"^\s*\\(.+)$", line)
                if match is not None:
                    # identify
                    content = match.group(1)
                    if not " " in content:  # only a ref
                        tag_ref = content.strip()
                        tag_value = None
                    else:  # ref and value
                        match = re.search(r"^([\w\-\>\<:]+) (.*)$", content)
                        tag_ref = match.group(1)
                        tag_value = match.group(2).strip()
                    # store
                    if fieldd is None:  # we are not in a field -> object descriptor comment
                        od.add_tag(tag_ref, tag_value)
                    else:  # we are in a field
                        fieldd.add_tag(tag_ref, tag_value)
                    continue

                # named field descriptor
                match = re.search(r"^\s*([AN])\d+\s*([;,])\s*\\[fF]ield (.*)$", line)
                if match is not None:
                    # identify
                    fieldd_type = match.group(1)
                    name = match.group(3).strip()
                    if name == "":
                        name = None
                    # store
                    fieldd = FieldDescriptor(fieldd_type, name=name)
                    od.add_field_descriptor(fieldd)
                    continue

                # unnamed field descriptors
                match = re.search(r"^\s*[AN]\d+.+([;,])\s*\\note.*$", line)
                if match is not None:
                    # identify
                    fields_l = [s.strip() for s in line.split(r"\note")[0].strip()[:-1].split(",")]
                    for fieldd_s in fields_l:
                        fieldd_type = fieldd_s[0]
                        # store
                        fieldd = FieldDescriptor(fieldd_type)
                        od.add_field_descriptor(fieldd)
                    continue

                # od: object descriptor
                match = re.search(r"^\s*([\w:\-]+),\s*$", line)
                if match is not None:
                    # identify
                    ref = match.group(1).strip()
                    if group_name is None:
                        raise IDDError("No group name.")
                    # store
                    od = ObjectDescriptor(ref, group_name=group_name)
                    if ref in self._ods_d:
                        raise IDDError("Object descriptor already registered.")
                    self._ods_d[ref.lower()] = od
                    self._groups_d[group_name].append(od)

                    # re-initialize
                    fieldd = None
                    continue

                # non parsed line - special objects
                if ("Lead Input;" in line) or ("Simulation Data;" in line):
                    # store
                    ref = line.strip()[:-1]
                    self._ods_d[ref.lower()] = ObjectDescriptor(ref)  # start
                    self._ods_d["end " + ref.lower()] = ObjectDescriptor("End " + ref)  # end
                    # re-initialize
                    od, fieldd = None, None
                    continue

                raise IDDError("Line %i not parsed: '%s'." % (i+1, raw_line))

    def _link(self):
        """ Links object descriptors together. """
        for od in self._ods_d.values():
            for i, fieldd in enumerate(od.field_descriptors_l):
                if fieldd.has_tag("reference"):
                    for ref_name in fieldd.get_tag("reference"):
                        if not ref_name in self._pointed_od_linkds_d:
                            self._pointed_od_linkds_d[ref_name] = []
                        self._pointed_od_linkds_d[ref_name].append((od, i))
                if fieldd.has_tag("object-list"):
                    for ref_name in fieldd.get_tag("object-list"):
                        if not ref_name in self._pointing_od_linkds_d:
                            self._pointing_od_linkds_d[ref_name] = []
                        self._pointing_od_linkds_d[ref_name].append((od, i))

    def get_object_descriptor(self, od_ref):
        """
        Arguments
        ---------
        od_ref: object descriptor reference.

        Returns
        -------
        object descriptor
        """

        return self._ods_d[od_ref.lower()]

    def get_object_descriptors_by_group(self, group_name):
        """
        Returns
        -------
        list of object descriptors belonging to a given group.
        """
        return self._groups_d[group_name]