class Hook:
    def __init__(self, index, references, value):
        """
        status:
            if target_record is None: inert
            if target_record is not None: activated
            
        value must always be relevant : !! don't forget to deactivate hook if field of record changes !!
        """
        self.index = index
        self.references = references
        self.value = value
        self.target_record = None

    @property
    def relations_manager(self):
        return self.target_record.get_epm()._dev_relations_manager

    def activate(self, target_record):
        self.target_record = target_record
        self.relations_manager.register_hook(self)

    def unregister(self):
        self.relations_manager.unregister_hook(self)
    
    def serialize(self):
        return self.value

