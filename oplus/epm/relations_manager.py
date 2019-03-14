from .multi_table_queryset import MultiTableQueryset
from .exceptions import FieldValidationError


class RelationsManager:
    """
    record: add hook field
        record
            create inert hook
            hook.activate => activate hook and relations_manager.register_hook
        relations_manager
            register hook

    record: add link field
        record
            create inert link
            link.activate => activate link and relations_manager.register_link
        relations_manager
            register link

    record: remove hook
        record
            hook.unregister => relations_manager.unregister_hook
            set None inert

        relations_manager
            find pointing records and field index
                link = record._dev_pop_link(index) (and check if required)
                relations_manager.unregister_link(link)
            unregister hook

    record: remove link
        record
            link.unregister => relations_manager.unregister_link
            set None inert
        relations_manager
            unregister link
    """
    def __init__(self, epm):
        self._epm = epm
        self._hooks = {}  # {(hook_ref, value): hook, ...
        self._links_by_source = {}  # {source_record: links_set, ...}
        self._links_by_target = {}  # {target_record: links_set, ...}
        
    def register_hook(self, hook):
        """
        target record must have been set
        """
        for key in hook.keys:
            if key in self._hooks:
                field_descriptor = hook.target_record.get_field_descriptor(hook.index)
                raise FieldValidationError(
                    f"Reference key already exists, can't create: {key}. "
                    f"{field_descriptor.get_error_location_message(hook.value)}"
                )
            self._hooks[key] = hook

    def register_link(self, link):
        """
        source record and index must have been set
        """
        key = (link.hook_ref, link.initial_hook_value)
        hook = self._hooks.get(key)
        if hook is None:
            field_descriptor = link.source_record.get_field_descriptor(link.source_index)
            raise FieldValidationError(
                f"No object found with given reference : {key}. "
                f"{field_descriptor.get_error_location_message(link.source_index)}"
            )
        link.set_target(self._hooks[key].target_record, hook.index)

        # store by source
        if link.source_record not in self._links_by_source:
            self._links_by_source[link.source_record] = set()
        self._links_by_source[link.source_record].add(link)

        # store by target
        if link.target_record not in self._links_by_target:
            self._links_by_target[link.target_record] = set()
        self._links_by_target[link.target_record].add(link)

    def unregister_hook(self, hook):
        # find records pointing on hook
        for link in self._links_by_target.get(hook.target_record, set()):
            # check it is pointing on correct index
            if link.target_index != hook.index:
                continue

            # set link field to none on source record
            link.source_record._dev_set_none_without_unregistering(hook.index)

            # unregister link
            link.unregister()

        # unregister hook
        for key in hook.keys:
            self._hooks.pop(key)

    def unregister_link(self, link):
        self._links_by_target[link.target_record].remove(link)
        self._links_by_source[link.source_record].remove(link)
        
    def get_pointing_on(self, target_record):
        return MultiTableQueryset(
            self._epm,
            (l.source_record for l in self._links_by_target.get(target_record, set()))
        )    
    
    def get_pointed_from(self, source_record):
        return MultiTableQueryset(
            self._epm,
            (l.target_record for l in self._links_by_source.get(source_record, set()))
        )
