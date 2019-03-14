import itertools


class Hook:
    def __init__(self, table_name, index, value, references, class_references):
        """
        status:
            if target_record is None: inert
            if target_record is not None: activated
            
        value must always be relevant : !! don't forget to deactivate hook if field of record changes !!
        """
        self.index = index
        self.value = value
        self.references = references
        self.class_value = table_name.lower()
        self.class_references = class_references
        self.target_record = None

    @property
    def keys(self):
        return itertools.chain(
            ((ref, self.value) for ref in self.references),
            ((ref, self.class_value) for ref in self.class_references)
        )

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

