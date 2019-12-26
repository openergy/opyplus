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
import re
import logging

from ..conf import CONF
from ..util import to_buffer, version_str_to_version
from .idd_debug import correct_idd
from .table_descriptor import TableDescriptor
from .resources import get_idd_path

logger = logging.getLogger(__name__)


_IDD_CACHE = {}  # {(major, minor): idd,... stores standard idds to prevent from parsing them each time


class Idd:
    version = None
    build = None

    def __init__(self, version_or_buffer_or_path=None, apply_corrections=True):
        # prepare variables
        if version_or_buffer_or_path is None:
            buffer_or_path = get_idd_path(CONF.default_idd_version)
        elif isinstance(version_or_buffer_or_path, (tuple, list)):
            buffer_or_path = get_idd_path(version_or_buffer_or_path)
        else:
            buffer_or_path = version_or_buffer_or_path

        # transform to buffer
        self.path, buffer = to_buffer(buffer_or_path)

        self.table_descriptors = dict()

        # parse
        with buffer as f:
            self._parse(f)

        # correct
        if apply_corrections:
            correct_idd(self)

        # prepare extensible table_descriptors
        for table_ref, table_descriptor in self.table_descriptors.items():
            table_descriptor.prepare_extensible()

    @classmethod
    def _dev_get_from_cache(cls, version):
        major, minor, patch = version
        if (major, minor) not in _IDD_CACHE:
            idd = cls(version_or_buffer_or_path=version)
            _IDD_CACHE[(major, minor)] = idd
        return _IDD_CACHE[(major, minor)]

    def _parse(self, open_buffer):
        # variables
        group_name, rd, field_descriptor = None, None, None

        # store version
        row = next(open_buffer)
        _, version_str = row.split("IDD_Version ")
        self.version = version_str_to_version(version_str)

        # store build
        row = next(open_buffer)
        row_l = row.split("IDD_BUILD ")
        if len(row_l) == 2:  # this row appeared in idd >= 8.2.0
            _, self.build = row.split("IDD_BUILD ")

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
                    rd.add_tag(tag_ref, tag_value)
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
                field_descriptor = rd.add_field_descriptor(fieldd_type, name=name)
                continue

            # unnamed field descriptors
            match = re.search(r"^\s*([AN]\d+[;,]\s*)+.*$", line)
            if match is not None:
                # identify
                fields_l = [s.strip() for s in match.group(1).strip()[:-1].split(",")]
                for fieldd_s in fields_l:
                    fieldd_type = fieldd_s[0]

                    # store
                    field_descriptor = rd.add_field_descriptor(fieldd_type)
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

            raise RuntimeError("Line %i not parsed: '%s'." % (i+3, raw_line))
