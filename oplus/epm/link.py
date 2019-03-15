

class Link:
    def __init__(self, hook_ref, hook_value):
        """
        initial_hook_value may become obsolete when activated
        """
        self.hook_ref = hook_ref
        self.initial_hook_value = hook_value
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
        
    def unregister(self):
        self.relations_manager.unregister_record_hook(self)
    
    def set_target(self, target_record=None, target_table=None):
        if target_record is not None:
            self.target_record = target_record
        elif target_table is not None:
            self.target_table = target_table
        else:
            raise AssertionError("shouldn't be here")
    
    def serialize(self):
        if self.target_record is not None:
            return self.target_record[0]
        if self.target_table is not None:
            return self.target_table.get_name().lower()
        raise AssertionError("shouldn't be here")
    
    def activate(self, source_record):
        # return if already active
        if self.source_record is not None:
            return
        self.source_record = source_record
        self.relations_manager.register_link(self)
