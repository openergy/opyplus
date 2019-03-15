

class RecordHook:
    def __init__(self, references, value):
        """
        target_value must always be relevant : !! don't forget to deactivate hook if field of record changes !!
        """
        self.references = references
        self.target_value = value
        self.target_record = None

    @property
    def keys(self):
        return ((ref, self.target_value) for ref in self.references)

    @property
    def relations_manager(self):
        return self.target_record.get_epm()._dev_relations_manager

    def activate(self, target_record):
        # return if already active
        if self.target_record is not None:
            return
        self.target_record = target_record
        self.relations_manager.register_record_hook(self)

    def unregister(self):
        self.relations_manager.unregister_record_hook(self)
    
    def serialize(self):
        return self.target_value

