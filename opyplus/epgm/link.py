"""Link module."""


class Link:
    """
    Link class, describing link between two Epgm records (IDF,DDY objects), or between an Epgm record and an Epgm table.

    Parameters
    ----------
    hook_references: list of str
    hook_value
    source_index: int

    Attributes
    ----------
    hook_references: list of str
    initial_hook_value
    source_index: int
    source_record: opyplus.epgm.record.Record or None
    target_record: opyplus.epgm.record.Record or None
    target_table: opyplus.epgm.table.Table or None

    Notes
    -----
    If target_table is None: target_record is necessarily not None and the link describes a record pointing on a table.
    If target_table is not None: target_record is necessarily None and the link describes a record pointing on a record.
    """

    def __init__(self, hook_references, hook_value, source_index):
        # initial_hook_value may become obsolete when activated
        self.hook_references = hook_references
        self.initial_hook_value = hook_value
        self.source_index = source_index
        self.source_record = None
        self.target_record = None
        self.target_table = None

    @property
    def relations_manager(self):
        """
        Get the relation manager managing this link.

        Returns
        -------
        opyplus.epgm.relations_manager.RelationsManager
        """
        return self.source_record.get_epgm()._dev_relations_manager

    @property
    def target(self):
        """
        Get the link target table or record.

        Returns
        -------
        opyplus.epgm.table.Table or opyplus.epgm.record.Record
        """
        if self.target_table is not None:
            return self.target_table
        if self.target_record is not None:
            return self.target_record
        raise AssertionError("should not be here")

    def activate(self, source_record):
        """
        Activate link with given source_record.

        Parameters
        ----------
        source_record: opyplus.epgm.record.Record
        """
        # return if already active
        if self.source_record is not None:
            return
        self.source_record = source_record
        self.relations_manager.register_link(self)
        # clear initial hook value to prevent future incorrect use
        self.initial_hook_value = None

    def set_target(self, target_record=None, target_table=None):
        """
        Set link target.

        Parameters
        ----------
        target_record: opyplus.epgm.record.Record or None
        target_table: opyplus.epgm.table.Table or None
        """
        if target_record is not None:
            self.target_record = target_record
        elif target_table is not None:
            self.target_table = target_table
        else:
            raise AssertionError("shouldn't be here")

    def unregister(self):
        """Unregister link."""
        self.relations_manager.unregister_link(self)

    def serialize(self):
        """
        Serialize link (return its target ref/name).

        Returns
        -------
        str
        """
        if self.target_record is not None:
            return self.target_record[0]
        if self.target_table is not None:
            return self.target_table.get_name().lower()
        raise AssertionError("shouldn't be here")


NONE_LINK = Link(None, None, None)
