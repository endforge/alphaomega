"""
File: translator_record.py

Purpose:
    Represents one canonical synchronization object produced by the
    Translator stage.

The Translator converts repository-specific objects into AlphaOmega's
canonical synchronization model. Each TranslatorRecord represents one
translated synchronization object that may later be evaluated by the
Discovery stage.
"""


class TranslatorRecord:
    """
    Represents one translated synchronization object.

    This record is mutable while owned by the Translator stage.
    After being added to a locked TranslatorSection, it becomes
    immutable as part of that section.
    """

    def __init__(self):
        """
        Initialize an empty TranslatorRecord.
        """

        #
        # Stable source identity
        #
        self.source_name = None
        self.source_object_id = None
        self.source_parent_object_id = None

        #
        # Canonical synchronization information
        #
        self.object_type = None
        self.name = None
        self.source_path = None

        #
        # Source metadata
        #
        self.source_created_at = None
        self.source_modified_at = None
        self.source_url = None

        #
        # Repository-independent metadata
        #
        self.metadata = {}