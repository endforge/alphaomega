class DiscoveryResult:
    """Stores the results of a discovery run."""

    def __init__(self):
        self.containers = []
        self.content = []

"""
Discovery Result

Stores the results of a discovery run.
"""

from dataclasses import dataclass, field


@dataclass
class DiscoveryResult:
    """Results returned by the Discovery Service."""

    containers: list = field(default_factory=list)
    content: list = field(default_factory=list)