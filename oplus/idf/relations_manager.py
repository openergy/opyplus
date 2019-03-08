# todo: manage not unique error


class RelationsManager:
    def __init__(self):
        self._hooks = {}  # {(hook_ref, value): target_record, ...
        self._links = {}
        
    def add_hooks(self, references, value, target_record):
        initial_len = len(self._hooks)
        for ref in references:
            self._hooks[(ref, value)] = target_record
        if len(self._hooks) != initial_len + len(references):
            raise RuntimeError("not unique")
        
    def add_link(self, hook_ref, value, source_record):
        # todo: to be continued
