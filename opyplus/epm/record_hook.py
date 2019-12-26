class RecordHook:
    def __init__(self, references, index, value):
        """
        target_value must always be relevant : !! don't forget to deactivate hook if field of record changes !!
        """
        self.references = references
        self.target_index = index
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

    def update(self, new_target_value):
        # store old keys
        old_keys = tuple(self.keys)  # force iteration to prevent from obsolescence

        # modify target_value
        self.target_value = new_target_value

        # inform relations_manager
        self.relations_manager.record_hook_value_was_updated(self, old_keys)

    def unregister(self):
        self.relations_manager.unregister_record_hook(self)

    def serialize(self):
        return self.target_value


NONE_RECORD_HOOK = RecordHook(None, None, None)
