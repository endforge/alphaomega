"""
File: sync_state.py

Purpose:
    Defines the synchronization states assigned by Discovery.
"""

from enum import Enum


class SyncState(Enum):
    """
    Represents the synchronization state of a source object
    relative to the Canonical Knowledge Repository.
    """

    NEW = "NEW"
    MODIFIED = "MODIFIED"
    UNCHANGED = "UNCHANGED"