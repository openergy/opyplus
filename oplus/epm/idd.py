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
from .table_descriptor import TableDescriptor


logger = logging.getLogger(__name__)


def get_idd_standard_path():
    return os.path.join(CONF.eplus_base_dir_path, "Energy+.idd")


class Idd:
    def __init__(self, buffer_or_path=None, encoding=None):
        # prepare variables
        self.encoding = CONF.encoding if encoding is None else encoding
        if buffer_or_path is None:
            buffer_or_path = get_idd_standard_path()
        if isinstance(buffer_or_path, str):
            if not os.path.isfile(buffer_or_path):
                raise FileNotFoundError(f"no idd found at given path: {buffer_or_path}")
            self.path = buffer_or_path
            buffer = open(buffer_or_path, encoding=self.encoding)
        else:
            self.path = None
            buffer = buffer_or_path

        self.table_descriptors = dict()

        # parse
        with buffer as f:
            self._parse(f)

        # prepare extensible table_descriptors
        for table_ref, table_descriptor in self.table_descriptors.items():
            table_descriptor.prepare_extensible()

    def _parse(self, open_buffer):
        # variables
        group_name, rd, field_descriptor = None, None, None
        
        # iter
        for i, raw_line in enumerate(open_buffer):
            line = raw_line.split("!")[0]  # we tear comment

            # blank line
            if re.search(r"^\s*$", line) is not None:
                continue

            # group comment (must be before comments)
            match = re.search(r"^\\group (.+)$", line)
            if match is not None:
                group_name = match.group(1).strip()
                # self._groups_d[group_name.lower()] = dict(name=group_name, record_descriptors=[])

                # re-initialize
                rd, field_descriptor = None, None
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
                if field_descriptor is None:  # we are not in a field -> record descriptor comment
                    rd._add_tag(tag_ref, tag_value)
                else:  # we are in a field
                    field_descriptor.append_tag(tag_ref, tag_value)
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
                field_descriptor = FieldDescriptor(fieldd_type, name=name)
                rd._append_field_descriptor(field_descriptor)
                continue

            # unnamed field descriptors
            match = re.search(r"^\s*([AN]\d+([;,])\s*)+\\note.*$", line)
            if match is not None:
                # identify
                fields_l = [s.strip() for s in line.split(r"\note")[0].strip()[:-1].split(",")]
                for fieldd_s in fields_l:
                    fieldd_type = fieldd_s[0]

                    # store
                    field_descriptor = FieldDescriptor(fieldd_type)
                    rd._append_field_descriptor(field_descriptor)
                continue

            # rd: record descriptor
            match = re.search(r"^\s*([\w:\-]+),\s*$", line)
            if match is not None:
                # identify
                table_name = match.group(1).strip()
                if group_name is None:
                    raise RuntimeError("no group name")

                # store
                rd = TableDescriptor(table_name, group_name=group_name)
                if rd.table_ref in self.table_descriptors:
                    raise RuntimeError("record descriptor already registered")
                self.table_descriptors[rd.table_ref.lower()] = rd
                # self._groups_d[group_name.lower()]["record_descriptors"].append(rd)

                # re-initialize
                field_descriptor = None
                continue

            # skip special tables
            if ("lead input;" in line.lower()) or ("simulation data;" in line.lower()):
                # re-initialize
                rd, field_descriptor = None, None
                continue

            raise RuntimeError("Line %i not parsed: '%s'." % (i+1, raw_line))
