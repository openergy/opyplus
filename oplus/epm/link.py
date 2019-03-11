class Link:
    def __init__(self, hook_ref, hook_value):
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
        self.target_record = None
        
    def deactivate(self):
        pass
        # todo: code and create obsolete status
    
    def set_target_record(self, target_record):
        self.target_record = target_record
    
    def serialize(self):
        # todo: code
        return self.initial_hook_value # if self.source_record is None else code
    
    def activate(self, source_record):
        self.source_record = source_record
        source_record.get_epm()._dev_add_link(self)
