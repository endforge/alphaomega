"""
File: connector_section.py

Purpose:
    Stores the raw output produced by the Connector stage
    during a synchronization run.
"""

from scripts.sync.sync_base_section import BaseSection


class ConnectorSection(BaseSection):
    """
    Contains the raw information retrieved from a Source of Truth.

    The Connector stage owns this section.
    It may populate the section while it is unlocked.
    After the Connector stage completes successfully, the section is locked and becomes read-only for all downstream stages.
    """

    section_name = "connector"

    def __init__(self, source_name):
        """
        Initialize an empty Connector section for a source.
        """

        super().__init__()

        self.source_name = source_name
        self.object_type = None
        self.connection_succeeded = False
        self.raw_objects = []
        self.raw_metadata = {}