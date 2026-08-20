"""
AlphaOmega Credential Provider Interface

Defines the stable interface used by AlphaOmega infrastructure to retrieve
credentials without depending on a specific credential-storage technology.
"""

from abc import ABC, abstractmethod


class CredentialProvider(ABC):
    """Base interface for AlphaOmega credential providers."""

    @abstractmethod
    def get(self, credential_name: str) -> str:
        """
        Retrieve a credential using its logical AlphaOmega name.

        Args:
            credential_name: Logical name of the requested credential.

        Returns:
            The requested secret.

        Raises:
            ValueError: If the credential name is invalid.
            RuntimeError: If the credential cannot be retrieved.
        """
        raise NotImplementedError