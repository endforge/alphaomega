"""
File: discovery_record.py

Purpose:
    Represents the synchronization decision produced by Discovery
    for one translated source object.
"""


class DiscoveryRecord:
    """
    Stores Discovery-owned synchronization information for one object.

    Translator-owned information remains in the TranslatorRecord.
    Discovery does not copy, modify, or reinterpret upstream fields.
    """

    def __init__(self):
        """
        Initialize an empty DiscoveryRecord.
        """

        #
        # Resolved AlphaOmega identity
        #
        self.knowledge_object_id = None

        #
        # Discovery synchronization decision
        #
        self.sync_state = None
        self.comparison_reason = None
        self.previous_content_hash = None
        self.requires_extraction = None