class Hook:
    def __init__(self, references, value):
        """
        status:
            if target_record is None: inert
            if target_record is not None: activated
            
        value must always be relevant : !! don't forget to deactivate hook if field of record changes !!
        """
        self.references = references
        self.value = value
        self.target_record = None

    def activate(self, target_record):
        self._target_record = target_record
        target_record.get_epm()._dev_add_hook(self)

    def deactivate(self):
        pass
        # todo: code and create obsolete status
    
    def serialize(self):
        return self.value

