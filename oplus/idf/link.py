class Link:
    def __init__(self, reference, value):
        self._pre_activation_info = (reference, value)
        
    def deactivate(self):
        pass
        # todo: code
    
    def serialize(self):
        # todo: code (this will not work!!)
        return self._pre_activation_info[1]
