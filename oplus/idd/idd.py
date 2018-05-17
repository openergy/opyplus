"""
Idd
---
Manages the EPlus idd file.

Definitions
-----------
record: EPlus object
field: EPlus object field
record descriptor: description of a record, given by the idd. A record descriptor has a unique ref (given by idd)
field descriptor: descriptor of a field of a record

pointing records (has tag 'object-list'): object that points towards another object
pointed record (has tag 'reference'): object being pointed by another object

"""

import os
import re
import logging
from collections import OrderedDict

from oplus.configuration import CONF

from .field_descriptor import FieldDescriptor
from .record_descriptor import RecordDescriptor


logger = logging.getLogger(__name__)


def get_idd_path():
    return os.path.join(CONF.eplus_base_dir_path, "Energy+.idd")


class Idd:
    @classmethod
    def get_idd(cls, idd_or_path, encoding=None):
        if idd_or_path is None:
            return cls()
        if isinstance(idd_or_path, str):
            return cls(path=idd_or_path, encoding=encoding)
        elif isinstance(idd_or_path, cls):
            return idd_or_path
        raise ValueError(
            f"'idd_or_path' must be a path or an Idd. Given record: '{idd_or_path}', type: '{type(idd_or_path)}'."
        )

    def __init__(self, path=None, encoding=None):
        assert (path is None) or os.path.exists(path), "No file at given path: '%s'." % path
        self.path = get_idd_path() if path is None else path
        self._encoding = encoding

        # rd: record descriptor, linkd: link descriptor
        # istr: insensitive string
        self._rds_d = OrderedDict()  # record descriptors {table_descriptor_lower_ref: rd, ...}
        self._pointed_rd_linkds_d = {}  # linkd: link descriptor {link_lower_name: [(rd, field_index), ...], ...}
        self._pointing_rd_linkds_d = {}  # {link_lower_name: [(rd, field_index), ...], ...}
        self._groups_d = OrderedDict()  # {group_lower_name: {name: group_name, record_descriptors: [rd, rd, ...]}

        self._parse()
        self._link()

    def get_table_ref(self, insensitive_ref):
        rd = self._rds_d.get(insensitive_ref.lower())
        if rd is None:
            raise KeyError(f"unknown table: {insensitive_ref}")
        return rd.table_ref

    def pointed_links(self, link_insensitive_name):
        """
        Returns all the possible links named 'link_name' to pointed records. A link is a combination of an record
        descriptor and an index. This corresponds to fields having a 'reference' tag.

        Returns
        -------
        list of links: [(record_descriptor_ref (istr), index), ...]
        """
        link_lower_name = link_insensitive_name.lower()
        if link_lower_name not in self._pointed_rd_linkds_d:
            logger.info(
                f"Idd useless ref -> '{link_insensitive_name}' ref is defined, "
                f"but no object-list pointing (idd problem, nothing can be done)."
            )
            return []
        return self._pointed_rd_linkds_d[link_lower_name]

    def pointing_links(self, link_insensitive_name):
        """
        Returns all the possible links named 'link_name' to pointing records. A link is a combination of an record
        descriptor and an index. This corresponds to a field having an 'object-list' tag.

        Returns
        -------
        list of links: [(record_descriptor_ref, index), ...]
        """
        link_lower_name = link_insensitive_name.lower()
        if link_lower_name not in self._pointing_rd_linkds_d:
            logger.debug(
                f"No pointing links ('object-list') with name '{link_insensitive_name}'. "
                f"This may be an idd bug, or a wrong link_name may have been provided."
            )
            return []
        return self._pointing_rd_linkds_d[link_lower_name]

    @property
    def group_names(self):
        """
        All group names.
        """
        return [g["name"] for g in self._groups_d]

    def _parse(self):
        """ Parses idd file."""
        group_name, rd, fieldd = None, None, None
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
                    self._groups_d[group_name.lower()] = dict(name=group_name, record_descriptors=[])

                    # re-initialize
                    rd, fieldd = None, None
                    continue

                # tag
                match = re.search(r"^\s*\\(.+)$", line)
                if match is not None:
                    # identify
                    content = match.group(1)
                    if " " not in content:  # only a ref
                        tag_ref = content.strip()
                        tag_value = None
                    else:  # ref and value
                        match = re.search(r"^([\w\-\>\<:]+) (.*)$", content)
                        tag_ref = match.group(1)
                        tag_value = match.group(2).strip()

                    # store
                    if fieldd is None:  # we are not in a field -> record descriptor comment
                        rd.add_tag(tag_ref, tag_value)
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
                    rd.add_field_descriptor(fieldd)
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
                        rd.add_field_descriptor(fieldd)
                    continue

                # rd: record descriptor
                match = re.search(r"^\s*([\w:\-]+),\s*$", line)
                if match is not None:
                    # identify
                    ref = match.group(1).strip()
                    assert group_name is not None, "No group name."

                    # store
                    rd = RecordDescriptor(ref, group_name=group_name)
                    assert ref not in self._rds_d, "Record descriptor already registered."
                    self._rds_d[ref.lower()] = rd
                    self._groups_d[group_name.lower()]["record_descriptors"].append(rd)

                    # re-initialize
                    fieldd = None
                    continue

                # non parsed line - special records
                if ("Lead Input;" in line) or ("Simulation Data;" in line):
                    # store
                    ref = line.strip()[:-1]
                    self._rds_d[ref.lower()] = RecordDescriptor(ref)  # start
                    end = "End " + ref
                    self._rds_d[end.lower()] = RecordDescriptor(end)  # end

                    # re-initialize
                    rd, fieldd = None, None
                    continue

                raise RuntimeError("Line %i not parsed: '%s'." % (i+1, raw_line))

    def _link(self):
        """ Links record descriptors together. """
        for rd in self._rds_d.values():
            for i, fieldd in enumerate(rd.field_descriptors_l):
                if fieldd.has_tag("reference"):
                    for ref_name in fieldd.get_tag("reference"):
                        ref_lower_name = ref_name.lower()
                        if ref_lower_name not in self._pointed_rd_linkds_d:
                            self._pointed_rd_linkds_d[ref_lower_name] = []
                        self._pointed_rd_linkds_d[ref_lower_name].append((rd, i))
                if fieldd.has_tag("object-list"):
                    for ref_name in fieldd.get_tag("object-list"):
                        ref_lower_name = ref_name.lower()
                        if ref_lower_name not in self._pointing_rd_linkds_d:
                            self._pointing_rd_linkds_d[ref_lower_name] = []
                        self._pointing_rd_linkds_d[ref_lower_name].append((rd, i))

    def get_record_descriptor(self, rd_insensitive_ref):
        """
        Arguments
        ---------
        rd_insensitive_ref: record descriptor reference.

        Returns
        -------
        record descriptor
        """
        return self._rds_d[rd_insensitive_ref.lower()]

    def get_record_descriptors_by_group(self, group_insensitive_name):
        """
        Returns
        -------
        list of record descriptors belonging to a given group.
        """
        return self._groups_d[group_insensitive_name.lower()]["record_descriptors"]
