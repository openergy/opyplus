import io
import itertools
from oplus import CONF  # todo: change conf style ?
from contextlib import contextmanager
from oplus.idf.idd import Idd
from .table import Table
from .queryset import Queryset
from .cache import CachedMixin, cached, clear_cache
from .record import Record
from .links_manager import LinksManager
from .hooks_manager import HooksManager
from ..util import get_string_buffer
from .style import IdfStyle, style_library
from .exceptions import BrokenIdfError, IsPointedError
from ..idf.table_descriptor import table_name_to_ref
from .idf_parse import parse_idf


# todo: it seams that we removed head comments
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
        # todo: should all tables be loaded ?
        self._tables = dict([  # {lower_ref: table, ...}
            (table_descriptor.table_ref.lower(), Table(table_descriptor, self))
            for table_descriptor in self._dev_idd.table_descriptors.values()
        ])
        
        self._dev_path = None

        # prepare hooks and links managers
        self._hooks_manager = HooksManager()
        self._links_manager = LinksManager()
        
        # parse if relevant
        if path_or_content is not None:
            # get string buffer and store path (for info)
            buffer, path = get_string_buffer(path_or_content, "idf", self._encoding)
            self._dev_path = path_or_content

            # raw parse and parse
            with buffer as f:
                json_data = parse_idf(f, style=style)
                
            # populate
            self._dev_populate_from_json_data(json_data)

    @classmethod
    def from_json_data(cls, json_data):
        idf = cls()
        idf._dev_populate_from_json_data(json_data)
        return idf

    def _dev_populate_from_json_data(self, json_data):
        added_records = []
        for table_ref, json_data_records in json_data.items():
            # find table
            table = getattr(self, table_ref)

            # add records (inert)
            added_records.extend(table._dev_add_inert(json_data_records))

        # activate hooks
        for r in added_records:
            r._dev_activate_hooks()

        # activate links
        for r in added_records:
            r._dev_activate_links()
            
    def _dev_check_references_uniqueness(self, modified_records):
        """
        Parameters
        ----------
        modified_records: all records that have modified
        """
        # todo
        pass

    # --------------------------------------------- public api ---------------------------------------------------------
    # python magic
    def __dir__(self):
        return [t.get_ref() for t in self._tables.values()] + [k for k in self.__dict__ if k[0] != "_"]

    def __getattr__(self, item):
        try:
            return self._tables[item.lower()]
        except KeyError:
            raise AttributeError(f"No table with reference '{item}'.")
        
    def to_str(self, style=None, add_copyright=True, sort=True, with_chapters=True):
        # todo: sort is now mandatory
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
        # #idf_comment = self._head_comments
        # if add_copyright:
        #     msg = self.copyright_comment()
        #     if msg not in idf_comment:
        #         idf_comment = msg + "\n" + idf_comment

        # for comment in idf_comment.split("\n")[:-1]:
        #     content += style.get_head_comment(comment)

        # prepare records content [(table_ref, record_str), ...]
        # formatted_records = [
        #     (obj.get_table_ref(), "\n%s" % obj.to_str(style="idf", idf_style=style)) for obj in self._records
        # ]
        
        formatted_records = []
        for table_ref, table in sorted(self._tables.items()):
            # todo: manage options
            # todo: sort
            formatted_records.extend([r.to_str() for r in table._records.values()])  # iter table instead of using private _records
            
        return "\n\n".join(formatted_records)

        # # sort if asked
        # if sort:
        #     formatted_records = sorted(formatted_records)

        # todo: do we manage chapters ??
        # iter
        # current_ref = None
        # for (record_ref, record_str) in formatted_records:
        #     # write chapter title if needed
        #     if with_chapters and (record_ref != current_ref):
        #         current_ref = record_ref
        #         content += "\n" + style.get_chapter_title(current_ref)
        # 
        #     # write record
        #     content += record_str

        # return content















