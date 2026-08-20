"""
File: extraction_section.py

Purpose:
    Stores the output produced by the Extraction stage
    during a synchronization run.
"""

from scripts.sync.sync_base_section import BaseSection


class ExtractionSection(BaseSection):
    """
    Contains the extraction records and record-level
    errors produced by the Extraction stage.

    The Extraction stage owns this section.

    After the Extraction stage completes, the section is locked and
    becomes read-only for all downstream stages.
    """

    section_name = "extraction"

    def __init__(self):
        """
        Initialize an empty Extraction section.
        """

        super().__init__()

        self.extraction_records = []
        self.record_errors = []

        self.extraction_succeeded = False