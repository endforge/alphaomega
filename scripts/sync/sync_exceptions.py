"""
Synchronization exceptions.

Custom exceptions used throughout the synchronization pipeline.
"""


class SectionLockedError(Exception):
    """
    Raised when attempting to modify a synchronization section
    after it has been locked.
    """