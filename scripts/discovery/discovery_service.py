"""
Discovery Service

Coordinates discovery operations for any supported source.
"""

from .discovery_result import DiscoveryResult


class DiscoveryService:
    """Coordinates discovery for a connector."""

    def __init__(self, connector):
        self._connector = connector

    def discover(self) -> DiscoveryResult:
        """Discover objects requiring processing."""

        result = DiscoveryResult()

        return result