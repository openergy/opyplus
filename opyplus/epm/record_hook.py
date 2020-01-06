"""Opyplus epm package record_hook module.

A record hook is a record's field on which another record can point.
"""


class RecordHook:
    """
    RecordHook class.

    Parameters
    ----------
    references: EnergyPlus fields references
    index: field index
    value: field value

    Attributes
    ----------
    references: EnergyPlus fields references
    target_index: field index
    target_value: field value
    target_record: owner of the hook
    """

    def __init__(self, references, index, value):
        # target_value must always be relevant : !! don't forget to deactivate hook if field of record changes !!
        self.references = references
        self.target_index = index
        self.target_value = value
        self.target_record = None

    @property
    def keys(self):
        """
        Get this record_hook keys.

        A key is the couple (reference, target_value).

        Returns
        -------
        list of (str, target_value)
        """
        return ((ref, self.target_value) for ref in self.references)

    @property
    def relations_manager(self):
        """
        Get the relations manager.

        Returns
        -------
        opyplus.epm.relations_manager.RelationsManager
        """
        return self.target_record.get_epm()._dev_relations_manager

    def activate(self, target_record):
        """
        Activate the record hook.

        Attaches given record as owner of the hook, and registers hook in it's relations manager.

        Parameters
        ----------
        target_record
        """
        # return if already active
        if self.target_record is not None:
            return
        self.target_record = target_record
        self.relations_manager.register_record_hook(self)

    def update(self, new_target_value):
        """
        Change this record hook target.

        Parameters
        ----------
        new_target_value
        """
        # store old keys
        old_keys = tuple(self.keys)  # force iteration to prevent from obsolescence

        # modify target_value
        self.target_value = new_target_value

        # inform relations_manager
        self.relations_manager.record_hook_value_was_updated(self, old_keys)

    def unregister(self):
        """Unregisters this record hook and remove all it's pointing links."""
        self.relations_manager.unregister_record_hook(self)

    def serialize(self):
        """Serialize the record hook using its target value."""
        return self.target_value


NONE_RECORD_HOOK = RecordHook(None, None, None)
