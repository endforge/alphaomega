"""
Content Discovery Record

Represents a discovered content object.
Examples:
    - OneNote Page
    - OneDrive File
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContentRecord:
    source_id: str
    source_object_id: str
    object_type: str
    display_name: str

    parent_object_id: str | None
    source_path: str

    source_modified_at: datetime
    discovered_at: datetime

    processing_reason: str