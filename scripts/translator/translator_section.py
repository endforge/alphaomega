"""
File: translator_section.py

Purpose:
    Stores the output produced by the Translator stage
    during a synchronization run.
"""

from scripts.sync.sync_base_section import BaseSection


class TranslatorSection(BaseSection):
    """
    Contains the canonical synchronization records and record-level
    errors produced by the Translator stage.

    The Translator stage owns this section.

    After the Translator stage completes, the section is locked and
    becomes read-only for all downstream stages.
    """

    section_name = "translator"

    def __init__(self):
        """
        Initialize an empty Translator section.
        """

        super().__init__()

        self.translated_records = []
        self.record_errors = []

        self.translation_succeeded = False