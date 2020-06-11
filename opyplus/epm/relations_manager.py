"""Relation managers allow to handle links between different Epm records (idf objects)."""

from .multi_table_queryset import MultiTableQueryset
from ..exceptions import FieldValidationError


class RelationsManager:
    """
    Relation manager class to handle links between different Epm records (idf objects).

    Parameters
    ----------
    epm: opyplus.Epm

    Notes
    -----
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
            find pointing links
                pointing_record.set_non_inert
                link.unregister

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
        self._table_hooks = {}  # {(hook_ref, table_lower_name): table, ...}
        self._record_hooks = {}  # {(hook_ref, value): hook, ...
        self._links_by_source = {}  # {source_record_or_table: links_set, ...}
        self._links_by_target = {}  # {target_record_or_table: links_set, ...}

    def register_record_hook(self, hook):
        """
        Register a record hook.

        Parameters
        ----------
        hook: opyplus.epm.record_hook.RecordHook

        Notes
        -----
        target record must have been set
        """
        for key in hook.keys:
            if key in self._record_hooks:
                field_descriptor = hook.target_record.get_field_descriptor(hook.target_index)
                raise FieldValidationError(
                    f"Reference key already exists, can't create: {key}. "
                    f"{field_descriptor.get_error_location_message(hook.target_value, hook.target_index)}"
                )
            self._record_hooks[key] = hook

    def record_hook_value_was_updated(self, hook, old_keys):
        """
        Handle record_hook value update.

        Parameters
        ----------
        hook: opyplus.epm.record_hook.RecordHook
        old_keys: iterable of str
        """
        # remove old keys
        for key in old_keys:
            del self._record_hooks[key]

        # register with new keys
        self.register_record_hook(hook)

    def register_table_hook(self, references, table):
        """
        Register a new table hook.

        Parameters
        ----------
        references: list of str
        table: opyplus.epm.table.Table
        """
        table_lower_name = table.get_name().lower()
        for ref in references:
            self._table_hooks[(ref, table_lower_name)] = table

    def register_link(self, link):
        """
        Register a new link.

        Parameters
        ----------
        link: opyplus.epm.link.Link

        Notes
        -----
        source record and index must have been set
        """
        keys = tuple((ref, link.initial_hook_value) for ref in link.hook_references)

        # look for a record hook
        for k in keys:
            if k in self._record_hooks:
                # set link target
                link.set_target(target_record=self._record_hooks[k].target_record)
                break
        else:
            # look for a table hook
            for k in keys:
                if k in self._table_hooks:
                    # set link target
                    link.set_target(target_table=self._table_hooks[k])
                    break
            else:
                field_descriptor = link.source_record.get_field_descriptor(link.source_index)
                raise FieldValidationError(
                    f"No object found with any of given references : {keys}. "
                    f"{field_descriptor.get_error_location_message(link.initial_hook_value)}"
                )

        # store by source
        if link.source_record not in self._links_by_source:
            self._links_by_source[link.source_record] = set()
        self._links_by_source[link.source_record].add(link)

        # store by target
        if link.target not in self._links_by_target:
            self._links_by_target[link.target] = set()
        self._links_by_target[link.target].add(link)

    def unregister_record_hook(self, hook):
        """
        Unregister a record hook.

        Parameters
        ----------
        hook: opyplus.epm.record_hook.RecordHook
        """
        # find records pointing on record hook
        for link in self._links_by_target.get(hook.target_record, set()).copy():
            # set link field to none on source record
            link.source_record._dev_set_none_without_unregistering(link.source_index)

            # unregister link
            link.unregister()

        # unregister record hook
        for key in hook.keys:
            self._record_hooks.pop(key)

    def unregister_link(self, link):
        """
        Unregister a link.

        Parameters
        ----------
        link: opyplus.epm.link.Link
        """
        self._links_by_target[link.target].remove(link)
        if len(self._links_by_target[link.target]) == 0:
            del self._links_by_target[link.target]

        self._links_by_source[link.source_record].remove(link)
        if len(self._links_by_source[link.source_record]) == 0:
            del self._links_by_source[link.source_record]

    def get_pointing_on(self, target_record_or_table):
        """
        Get records pointing on a given table or record.

        Parameters
        ----------
        target_record_or_table: opyplus.epm.record.Record or opyplus.epm.table.Table

        Returns
        -------
        MultiTableQueryset
        """
        return MultiTableQueryset(
            self._epm,
            (link.source_record for link in self._links_by_target.get(target_record_or_table, set()))
        )

    def get_pointed_by(self, source_record):
        """
        Get records pointed by a given record.

        Parameters
        ----------
        source_record: opyplus.epm.record.Record

        Returns
        -------
        MultiTableQueryset
        """
        return MultiTableQueryset(
            self._epm,
            (link.target_record for link in self._links_by_source.get(source_record, set()))
        )
