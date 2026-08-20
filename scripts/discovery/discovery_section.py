"""
File: discovery_section.py

Purpose:
    Stores the output produced by the Discovery stage
    during a synchronization run.
"""

from scripts.sync.sync_base_section import BaseSection


class DiscoverySection(BaseSection):
    """
    Contains the synchronization records and record-level
    errors produced by the Discovery stage.

    The Discovery stage owns this section.

    After the Discovery stage completes, the section is locked and
    becomes read-only for all downstream stages.
    """

    section_name = "discovery"

    def __init__(self):
        """
        Initialize an empty Discovery section.
        """

        super().__init__()

        self.discovery_records = []
        self.record_errors = []

        self.discovery_succeeded = False