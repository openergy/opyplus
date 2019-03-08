class Hook:
    def __init__(self, references, value):
        self._pre_activation_info = (references, value)
        self._target_record = None
        # todo

    def activate(self, target_record):
        self._target_record = target_record
        target_record.get_idf()._dev_add_hook(
            self._pre_activation_info[0],
            self._pre_activation_info[1],
            target_record
        )

    def deactivate(self):
        pass
        # todo
    
    def serialize(self):
        # todo: code
        return self._value  # todo: this will not work, re-code !!

