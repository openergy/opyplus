import itertools


class Hook:
    def __init__(self, table_name, index, references):
        self.index = index
        self.value = self.table_name.lower()
        self.references = references

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
        # return if already active
        if self.target_record is not None:
            return
        self.target_record = target_record
        self.relations_manager.register_hook(self)

    def unregister(self):
        self.relations_manager.unregister_hook(self)

    def serialize(self):
        return self.value

