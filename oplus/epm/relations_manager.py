# todo: manage not unique error
# todo: manage hook not found error


class RelationsManager:
    def __init__(self):
        self._hooks = {}  # {(hook_ref, value): hook, ...
        self._links_by_source = {}  # {source_record: link, ...}
        self._links_by_target = {}  # {target_record: link, ...}
        
    def add_hook(self, hook):
        initial_len = len(self._hooks)
        for ref in hook.references:
            self._hooks[(ref, hook.value)] = hook
        if len(self._hooks) != initial_len + len(hook.references):
            raise RuntimeError("not unique")
        
    def add_link(self, link):
        key = (link.hook_ref, link.initial_hook_value)
        if key not in self._hooks:
            raise RuntimeError("hook not found")
        link.set_target_record(self._hooks[key])
        self._links_by_source[link.source_record] = link
        self._links_by_target[link.target_record] = link

    # todo: code remove hooks
