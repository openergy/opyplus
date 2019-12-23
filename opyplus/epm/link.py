class Link:
    def __init__(self, hook_references, hook_value, source_index):
        """
        initial_hook_value may become obsolete when activated
        """
        self.hook_references = hook_references
        self.initial_hook_value = hook_value
        self.source_index = source_index
        self.source_record = None
        self.target_record = None
        self.target_table = None

    @property
    def relations_manager(self):
        return self.source_record.get_epm()._dev_relations_manager

    @property
    def target(self):
        if self.target_table is not None:
            return self.target_table
        if self.target_record is not None:
            return self.target_record
        raise AssertionError("should not be here")

    def activate(self, source_record):
        # return if already active
        if self.source_record is not None:
            return
        self.source_record = source_record
        self.relations_manager.register_link(self)
        # clear initial hook value to prevent future incorrect use
        self.initial_hook_value = None

    def set_target(self, target_record=None, target_table=None):
        if target_record is not None:
            self.target_record = target_record
        elif target_table is not None:
            self.target_table = target_table
        else:
            raise AssertionError("shouldn't be here")

    def unregister(self):
        self.relations_manager.unregister_link(self)

    def serialize(self):
        if self.target_record is not None:
            return self.target_record[0]
        if self.target_table is not None:
            return self.target_table.get_name().lower()
        raise AssertionError("shouldn't be here")


NONE_LINK = Link(None, None, None)
