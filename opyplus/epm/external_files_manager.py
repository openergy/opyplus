import os

from opyplus import CONF


class ExternalFilesManager:
    def __init__(self, epm):
        self._epm = epm
        self._contents = dict()  # {ref: content_str, ...}
        self._external_files = set()

    def populate_from_json_data(self, json_data):
        """
        !! Must only be called once, when empty !!
        """
        self._contents = json_data

    @property
    def short_refs(self):
        """
        we calculate on the fly to avoid managing registrations and un-registrations

        Returns
        -------
        {ref: short_ref, ...
        """
        naive_short_refs_d = dict()  # naive_short_ref: {refs, ...}
        for ef in self._external_files:
            if ef.naive_short_ref not in naive_short_refs_d:
                naive_short_refs_d[ef.naive_short_ref] = set()
            naive_short_refs_d[ef.naive_short_ref].add(ef.ref)

        short_refs = dict()
        for naive_short_ref, refs in naive_short_refs_d.items():
            if len(refs) == 1:
                short_refs[refs.pop()] = naive_short_ref
                continue
            base, ext = os.path.splitext(naive_short_ref)
            for i, ref in enumerate(sorted(refs)):
                short_refs[ref] = f"{base}-{i}.{ext}"

        return short_refs

    def get_json_data(self):
        short_refs = self.short_refs
        return dict([(short_refs[ref], content) for (ref, content) in self._contents.items()])

    def contains(self, ref):
        return ref in self._contents

    def register(self, external_file):
        # store
        self._external_files.add(external_file)

        # leave if content is already here
        if external_file.ref in self._contents:
            return

        # prepare and store content
        self._contents[external_file.ref] = external_file._dev_prepare_content()

    def unregister(self, external_file):
        self._external_files.remove(external_file)

        # see if content is still needed
        for e in self._external_files:
            if e.ref == external_file.ref:  # still needed
                return
        # not needed
        del self._contents[external_file.ref]

    def get_content(self, ref):
        return self._contents[ref]

    def get_short_ref(self, external_file):
        naive_short_ref = external_file.naive_short_ref
        refs = tuple(sorted({e.ref for e in self._external_files if e.naive_short_ref == naive_short_ref}))
        if len(refs) == 1:
            return naive_short_ref
        base, ext = os.path.splitext(naive_short_ref)
        return base + "-" + str(refs.index(external_file.ref)) + "." + ext

    def dump_external_files(self, target_dir_path=None):
        # leave if no external files
        if len(self._contents) == 0:
            return

        # prepare directory
        if not os.path.exists(target_dir_path):
            os.mkdir(target_dir_path)

        # dump files
        for ref, short_ref in self.short_refs.items():
            with open(os.path.join(target_dir_path, short_ref), "w", encoding=CONF.encoding) as f:
                f.write(self._contents.get(ref, "TO BE FILLED"))
