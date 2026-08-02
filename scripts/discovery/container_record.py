"""
Container Discovery Record

Represents a discovered container object.
Examples:
    - OneNote Notebook
    - OneNote Section
    - OneDrive Folder
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContainerRecord:
    source_id: str
    source_object_id: str
    object_type: str
    display_name: str

    parent_object_id: str | None
    source_path: str

    source_modified_at: datetime
    discovered_at: datetime

    processing_reason: str