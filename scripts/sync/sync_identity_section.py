from scripts.sync.sync_base_section import SyncBaseSection


class SyncIdentitySection(SyncBaseSection):
    """
    Identifies a synchronization run.
    """

    @property
    def section_name(self) -> str:
        return "identity"

    def __init__(self):
        super().__init__()

        self.sync_run_id = None
        self.start_time = None