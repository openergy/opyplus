class Link:
    def __init__(self, source_index, hook_ref, hook_value):
        """
        status:
            if self.source_record is None: inert
            if self.source_record is not None and self.target_record is None: activating
            if self.target_record is not None: activated

        initial_hook_value may become obsolete when activated
        """
        self.hook_ref = hook_ref
        self.initial_hook_value = hook_value
        self.source_record = None
        self.source_index = source_index
        self.target_record = None
        self.target_index = None

    @property
    def relations_manager(self):
        return self.source_record.get_epm()._dev_relations_manager
        
    def unregister(self):
        self.relations_manager.unregister_hook(self)
    
    def set_target(self, target_record, target_index):
        self.target_record = target_record
        self.target_index = target_index
    
    def serialize(self):
        return self.initial_hook_value if self.target_record is None else self.target_record[self.target_index]
    
    def activate(self, source_record):
        self.source_record = source_record
        self.relations_manager.register_link(self)
