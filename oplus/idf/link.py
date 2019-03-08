class Link:
    def __init__(self, hook_ref, value):
        self._pre_activation_info = (hook_ref, value)
        
    def deactivate(self):
        pass
        # todo: code
    
    def serialize(self):
        # todo: code (this will not work!!)
        return self._pre_activation_info[1]
    
    def activate(self, source_record):
        source_record.get_idf()._dev_add_link(
            self._pre_activation_info[0],
            self._pre_activation_info[1],
            source_record
        )
